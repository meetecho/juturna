import pathlib
import inspect
import string
import time
import contextlib

from collections.abc import Callable

from typing import Any

import juturna as jt

from juturna.components import Message

from juturna.names import ComponentStatus
from juturna.utils.log_utils import jt_logger

from juturna.components._buffer import Buffer
from juturna.components._state import State
from juturna.telemetry import TelemetryManager
from juturna.components._synchronisers import _SYNCHRONISERS


_WAKE = object()


class Node[T_Input, T_Output]:
    """
    Use this class to design custom nodes. BaseNode comes with a number of
    utility methods and fields that can be either used as they are or extended
    in the derived classes.
    """

    def __init__(
        self,
        node_name: str = '',
        pipe_name: str = '',
        synchroniser: Callable | None = None,
        transport: jt.transport.TransportBackend | None = None,
    ):
        """
        Parameters
        ----------
        node_name : str
            The name to assign to the node.
        pipe_name : str
            The name of the pipe this node belongs to.
        synchroniser : Callable
            Management options for multi-input nodes.
        transport : TransportBackend
            The concurrency backend used to run and synchronise the node's
            internal workers. Defaults to a thread-based backend.

        """
        self.name = node_name
        self.pipe_name: str | None = pipe_name
        self.pipe_path: str | None = None
        self.pipe_id: str | None = None

        _logger_name = f'{self.pipe_name}.{self.name}'
        self.logger = jt_logger(_logger_name)
        self.logger.propagate = True

        self.synchroniser = synchroniser or (
            self.next_batch
            if hasattr(self, 'next_batch')
            else _SYNCHRONISERS['passthrough']
        )

        self._status: ComponentStatus | None = None
        self._state: State | None = None

        self._transport: jt.transport.TransportBackend = (
            transport or jt.transport.ThreadingTransport()
        )

        self._queue = self._transport.new_queue(
            maxsize=jt.meta.JUTURNA_MAX_QUEUE_SIZE
        )
        self._worker_thread: jt.transport.WorkerHandle | None = None
        self._source_thread: jt.transport.WorkerHandle | None = None
        self._update_thread: jt.transport.WorkerHandle | None = None

        self._stop_worker_event = self._transport.new_event()
        self._stop_source_event = self._transport.new_event()
        self._stop_update_event = self._transport.new_event()
        self._kill_event = self._transport.new_event()

        self._update_failures = 0
        self._source_failures = 0
        self._worker_failures = 0
        self._last_failure_at = None
        self._stuck_workers: list[str] = list()

        self._auto_dump = False

        self._buffer = Buffer(
            _logger_name,
            self.synchroniser,
            transport=self._transport,
            abort=self._kill_event,
        )

        self._source_f: Callable | None = None
        self._source_sleep = -1
        self._source_mode = ''

        self._destinations: dict[str, Node] = dict()
        self._origins: list = list()
        self._last_data_source_evt_id: int | None = None

        self._telemetry_buffer = list()
        self._telemetry_manager: TelemetryManager | None = None
        self._telemetry_lock: jt.transport.Lock = self._transport.new_lock()

    def __del__(self): ...

    @property
    def status(self) -> ComponentStatus | None:
        return self._status

    @property
    def configuration(self) -> dict:
        return {'name': self.name, 'session_id': self.pipe_id}

    @property
    def health(self) -> dict:
        """
        Counter of how many failues the node experienced across its threads.
        Values are split per-thread, so it will give the total for update,
        worker and source (if present).
        """
        return {
            'update_failures': self._update_failures,
            'worker_failures': self._worker_failures,
            'source_failures': self._source_failures,
            'last_failure_at': self._last_failure_at,
            'stuck_workers': list(self._stuck_workers),
        }

    @status.setter
    def status(self, new_status: ComponentStatus):
        self._status = ComponentStatus(new_status)

    @property
    def static_path(self) -> pathlib.Path:
        """
        Path to the directory where the node is defined. This is useful for
        storing static files (e.g. configuration files) that are needed by the
        node.
        """
        return pathlib.Path(inspect.getfile(self.__class__)).parent

    @property
    def origins(self) -> list:
        return self._origins

    @property
    def destinations(self) -> list:
        return list(self._destinations.keys())

    def link_telemetry(self, manager: TelemetryManager):
        self._telemetry_manager = manager

    def link_state(self, state: State):
        self._state = state

    def put(self, message: Message):
        while not self._kill_event.is_set():
            try:
                self._queue.put(message, timeout=0.1)

                return
            except jt.transport.Full:
                continue

    def compile_template(self, template_name: str, arguments: dict) -> str:
        """
        Compile a template string

        Parameters
        ----------
        template_name : str
            Path of the template.
        arguments : dict
            Dictionary of template anrguments and their values.

        Returns
        -------
        str
            Compiled template string.

        """
        _template_path = pathlib.Path(self.static_path, template_name)

        with open(_template_path) as f:
            _template_string = f.read()

        _content = string.Template(_template_string).substitute(arguments)

        return _content

    def prepare_template(
        self, template_name: str, file_destination_name: str, arguments: dict
    ) -> pathlib.Path:
        """
        Fetch a template file from the node folder, compile it, and save the
        produced file to the node pipeline folder. The template will be compiled
        with basic substitution of the passed arguments.

        Parameters
        ----------
        template_name : str
            The name of the template file to retrieve in the node folder.
        file_destination_name : str
            The name of the destination file in the node pipeline folder.
        arguments : dict
            The argument values to substitute in the template file.

        Returns
        -------
        pathlib.Path
            The path of the filed compiled and saved from the template.

        Raises
        ------
        ValueError
            If the node is not part of a pipeline, and pipe_path is not set.

        """
        if self.pipe_path is None:
            raise ValueError(
                'pipe_path is not set. '
                'Make sure the node is part of a pipeline.'
            )

        _destination_path = pathlib.Path(self.pipe_path, file_destination_name)
        _content = self.compile_template(template_name, arguments)

        with open(_destination_path, 'w') as f:
            f.write(_content)

        return _destination_path.resolve()

    def dump_json(self, message: Message, file_name: str) -> str | None:
        if self.pipe_path is None:
            return None

        dump_path = pathlib.Path(self.pipe_path, file_name)

        try:
            with open(dump_path, 'w') as f:
                f.write(message.to_json())
        except Exception:
            self.logger.warning('message cannot be dumped')

        return str(dump_path)

    def set_source(self, source: Callable, by: float = 0, mode: str = 'post'):
        """
        Set the node source (to be used for ``source`` nodes). The source is a
        callable invoked periodically: the message it returns is fed to the
        node, while ``None`` means there is nothing to deliver this time.

        Parameters
        ----------
        source : callable
            The function producing the messages of the node.
        by : float, optional
            The time interval (in seconds) between two consecutive calls to the
            source. With the default of 0 the source is called again right
            away, so it is expected to block until data is available.
        mode : str, optional
            Whether to apply the ``by`` timer before or after the source call.
            The default is ``post``: the source is called, then the node waits
            for ``by`` seconds before delivering the message (or before the next
            call, if the source returned ``None``). If set to ``pre``, the node
            waits for ``by`` seconds before every call.

        Notes
        -----
        An exception raised by the source is logged and counted in
        ``health``, and the next call is delayed by an exponential backoff
        starting at ``by`` (at least 0.1 seconds) and capped to
        ``JUTURNA_SOURCE_MAX_BACKOFF``, which resets at the first successful
        call.

        """
        self._source_f = source
        self._source_sleep = by
        self._source_mode = mode

    def add_destination(self, name: str, destination: 'Node'):
        self._destinations[name] = destination

    def clear_source(self): ...

    def clear_destination(self, name: str):
        del self._destinations[name]

    def clear_destinations(self):
        self._destinations = dict()

    def clear_buffer(self):
        self._buffer.flush()

    def transmit(self, message: Message[T_Output]):
        """
        Transmit a message. This method is used to send data from the node to
        its destinations. Messages are frozen before transmission, so that
        immutability is ensured.

        Parameters
        ----------
        message : Message | None
            The message to be transmitted.

        """
        object.__setattr__(
            message, '_data_source_id', self._last_data_source_evt_id
        )
        _ = message._freeze() if isinstance(message, Message) else None

        for node_name in self._destinations:
            self._destinations[node_name].put(message)

        if isinstance(message, Message):
            self._rec_telemetry(message, 'tx')

        if self._auto_dump:
            self.dump_json(message, f'auto_{message.id}.json')

    def start(self):
        """
        Start the node and begin processing. This method is called automatically
        when the parent pipeline is started. If you override this method in
        your custom node class, make sure to call the parent method to ensure
        the node is started correctly.
        """
        self._stop_source_event.clear()
        self._stop_worker_event.clear()
        self._stop_update_event.clear()
        self._kill_event.clear()

        if self._worker_thread is None:
            self._worker_thread = self._transport.spawn(
                target=self._worker,
                name=f'_worker_{self.name}',
                daemon=True,
            )

            self._worker_thread.start()
            self._status = ComponentStatus.RUNNING

        if self._update_thread is None:
            self._update_thread = self._transport.spawn(
                target=self._update,
                name=f'_update_{self.name}',
                daemon=True,
            )

            self._update_thread.start()

        if self._source_f is None:
            return

        if self._source_thread is None:
            self._source_thread = self._transport.spawn(
                target=self._source,
                name=f'_source_{self.name}',
                daemon=True,
            )

            self._source_thread.start()

    def stop(self):
        """
        Stop the node and begin processing. This method is called automatically
        when the parent pipeline is stopped. If you override this method in
        your custom node class, make sure to call the parent method to ensure
        the node is stopped correctly.

        Threads are stopped one at a time, each one after its upstream has
        terminated: source first, then worker, then update. Every thread
        consumes its own pending data before exiting, so all the messages
        received before the stop call are processed, and stop() waits for
        an ``update()`` call in progress to return, however long it takes.

        When the node is being killed (see ``kill()``), each thread is only
        waited for ``JUTURNA_THREAD_JOIN_TIMEOUT`` seconds: a thread still
        busy after that is left behind, and listed in ``health`` under
        ``stuck_workers``.
        """
        if self._status == ComponentStatus.STOPPED:
            return

        # the kill event is the only signal available here: subclasses call
        # super().stop() without arguments, so kill() cannot pass a timeout
        join_timeout = (
            jt.meta.JUTURNA_THREAD_JOIN_TIMEOUT
            if self._kill_event.is_set()
            else None
        )

        for _evt, _t, _wake in [
            (self._stop_source_event, self._source_thread, None),
            (self._stop_worker_event, self._worker_thread, self._wake_worker),
            (self._stop_update_event, self._update_thread, self._wake_update),
        ]:
            _evt.set()

            if _wake is not None:
                _wake()

            if _t is None or self._transport.is_current(_t):
                continue

            _t.join(timeout=join_timeout)

            if _t.is_alive():
                self._stuck_workers.append(_t.name)
                self.logger.warning(
                    f'worker {_t.name} did not exit within {join_timeout}s, '
                    'leaving it behind'
                )

        self._worker_thread = None
        self._source_thread = None
        self._update_thread = None
        self._status = ComponentStatus.STOPPED

        self.logger.info('node stopped')

    def signal_kill(self):
        """
        Signal all the node threads to exit without processing pending data.
        This method does not block: use ``kill()`` to wait for the threads to
        terminate and discard pending data.
        """
        self._kill_event.set()
        self._stop_source_event.set()
        self._stop_worker_event.set()
        self._stop_update_event.set()

        self._wake_worker()
        self._wake_update()

    def kill(self):
        """
        Stop the node without processing pending data. All threads are
        signalled at once and exit as soon as their current iteration is
        over: any message still in the input queue or in the buffer is
        discarded. Subclass cleanup in ``stop()`` still runs.

        Unlike ``stop()``, kill() does not wait for a busy ``update()`` or
        source call to return: each thread gets ``JUTURNA_THREAD_JOIN_TIMEOUT``
        seconds, then it is left behind (it exits on its own as soon as the
        call returns, without processing anything else).
        """
        if self._status == ComponentStatus.STOPPED:
            return

        self.signal_kill()
        self.stop()

        while True:
            try:
                self._queue.get_nowait()
            except jt.transport.Empty:
                break

        self.clear_buffer()

        self.logger.info('node killed')

    def join(self):
        """
        Wait for all internal threads to terminate.
        This method should be called after stop() to ensure the node has
        fully shut down before its resources are released.
        """
        for _t in [
            self._source_thread,
            self._worker_thread,
            self._update_thread,
        ]:
            if (
                _t is not None
                and _t.is_alive()
                and not self._transport.is_current(_t)
            ):
                _t.join(timeout=jt.meta.JUTURNA_THREAD_JOIN_TIMEOUT)

    def configure(self): ...

    def update(self, message: Message[T_Input], **kwargs): ...

    def set_on_config(self, prop: str, value: Any): ...

    def warmup(self): ...

    def destroy(self): ...

    def _wake_worker(self):
        with contextlib.suppress(jt.transport.Full):
            self._queue.put_nowait(_WAKE)

    def _wake_update(self):
        self._buffer.wake(_WAKE)

    def _worker(self):
        while not self._stop_worker_event.is_set():
            try:
                message = self._queue.get(
                    timeout=jt.meta.JUTURNA_THREAD_JOIN_TIMEOUT
                )
            except jt.transport.Empty:
                continue

            self._ingest(message)

        if self._kill_event.is_set():
            return

        while True:
            try:
                message = self._queue.get_nowait()
            except jt.transport.Empty:
                break

            self._ingest(message)

    def _update(self):
        while not self._stop_update_event.is_set():
            try:
                batch = self._buffer.get(
                    timeout=jt.meta.JUTURNA_THREAD_JOIN_TIMEOUT
                )
            except jt.transport.Empty:
                continue

            self._process(batch)

        if self._kill_event.is_set():
            return

        while True:
            try:
                batch = self._buffer.get_nowait()
            except jt.transport.Empty:
                break

            self._process(batch)

    def _source(self):
        consecutive_failures = 0

        while not self._stop_source_event.is_set():
            if self._source_mode == 'pre' and self._stop_source_event.wait(
                self._source_sleep
            ):
                return

            try:
                message = self._source_f()
            except Exception:
                consecutive_failures += 1
                self._source_failures += 1
                self._last_failure_at = time.time()
                self.logger.error(
                    f'unhandled exception in source function '
                    f'(failure {self._source_failures})',
                    exc_info=True,
                )

                if self._stop_source_event.wait(
                    self._source_backoff(consecutive_failures)
                ):
                    return

                continue

            consecutive_failures = 0

            if self._stop_source_event.is_set():
                continue

            # a source with nothing to deliver still waits, or a polling
            # source returning None would spin on the CPU
            if self._source_mode == 'post':
                self._stop_source_event.wait(self._source_sleep)

            if message is not None:
                self.put(message)

    def _source_backoff(self, consecutive_failures: int) -> float:
        """
        Time to wait after a failing call to the source function: ``by``
        seconds (at least 0.1) doubled at every consecutive failure, capped to
        ``JUTURNA_SOURCE_MAX_BACKOFF``.
        """
        base = max(self._source_sleep, 0.1)

        return min(
            base * 2 ** (consecutive_failures - 1),
            max(jt.meta.JUTURNA_SOURCE_MAX_BACKOFF, base),
        )

    def _ingest(self, message: Message):
        if message is _WAKE:
            return

        try:
            self._buffer.put(message)

            if isinstance(message, Message):
                self._rec_telemetry(message, 'rx')
        except Exception:
            self._worker_failures += 1
            self._last_failure_at = time.time()
            self.logger.error(
                f'unhandled exception in worker '
                f'(failure {self._worker_failures}), '
                f'message id {getattr(message, "id", "?")}',
                exc_info=True,
            )

    def _process(self, batch: Message):
        if batch is _WAKE:
            return

        self._last_data_source_evt_id = batch.id

        try:
            self.update(batch, state=self._state)
        except Exception:
            self._update_failures += 1
            self._last_failure_at = time.time()
            self.logger.error(
                f'unhandled exception in update() '
                f'(failure {self._update_failures}), '
                f'for message id {getattr(batch, "id", "?")}',
                exc_info=True,
            )

    def _rec_telemetry(self, message: Message, event: str):
        if self._telemetry_manager is None:
            return

        telemetry_entry = (
            time.time(),
            event,
            self.name,
            message.creator,
            message.id,
            message._data_source_id,
            getattr(message.payload, 'size_bytes', 0),
        )

        with self._telemetry_lock:
            self._telemetry_buffer.append(telemetry_entry)

            if (
                len(self._telemetry_buffer)
                < jt.meta.JUTURNA_TELEMETRY_BATCH_SIZE
            ):
                return

            batch, self._telemetry_buffer = self._telemetry_buffer, list()

        self._telemetry_manager.record_telemetry(batch)

    def flush_telemetry(self):
        """Send any buffered telemetry entries below the batch size"""
        if self._telemetry_manager is None:
            return

        with self._telemetry_lock:
            if not self._telemetry_buffer:
                return

            batch, self._telemetry_buffer = self._telemetry_buffer, list()

        self._telemetry_manager.record_telemetry(batch)
