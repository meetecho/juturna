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

from juturna.components._state import State
from juturna.telemetry import TelemetryManager


_WAKE = object()


class Node[T_Input, T_Output]:
    """
    Use this class to design custom nodes. BaseNode comes with a number of
    utility methods and fields that can be either used as they are or extended
    in the derived classes.
    """

    # returned by a state resolver to drop a message without processing it
    SKIP_UPDATE = object()

    def __init__(
        self,
        node_name: str = '',
        pipe_name: str = '',
        transport: jt.transport.TransportBackend | None = None,
    ):
        """
        Parameters
        ----------
        node_name : str
            The name to assign to the node.
        pipe_name : str
            The name of the pipe this node belongs to.
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

        self._status: ComponentStatus | None = None
        self._state: State | None = None
        self._state_resolver: Callable[[Message], Any] | None = None
        self._update_observer: (
            Callable[[Message, Exception | None], None] | None
        ) = None

        self._transport: jt.transport.TransportBackend = (
            transport or jt.transport.ThreadingTransport()
        )

        self._queue = self._transport.new_queue(
            maxsize=jt.meta.JUTURNA_MAX_QUEUE_SIZE
        )
        self._worker_thread: jt.transport.WorkerHandle | None = None
        self._source_thread: jt.transport.WorkerHandle | None = None

        self._stop_worker_event = self._transport.new_event()
        self._stop_source_event = self._transport.new_event()
        self._kill_event = self._transport.new_event()

        self._update_failures = 0
        self._source_failures = 0
        self._worker_failures = 0
        self._last_failure_at = None
        self._stuck_workers: list[str] = list()

        self._auto_dump = False

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

    def link_state_resolver(self, resolver: Callable[[Message], Any] | None):
        """
        Pick the state passed to ``update()`` for each message.

        By default every message is processed with the state linked by
        ``link_state()``. A node shared by several pipelines (the remote
        service) needs a different state per message instead: the resolver is
        called with the message about to be processed, on the update thread,
        and returns its state, or ``Node.SKIP_UPDATE`` to drop the message
        without calling ``update()``. ``None`` restores the default.
        """
        self._state_resolver = resolver

    def link_update_observer(
        self, observer: Callable[[Message, Exception | None], None] | None
    ):
        """
        Get notified every time ``update()`` returns.

        The observer is called on the update thread, after ``update()`` has
        processed a message, with that message and the exception it raised,
        or ``None``. Messages skipped by the state resolver are not reported.
        The remote service uses it to answer a request when its update is
        over, whether it transmitted something or not. ``None`` removes it.
        """
        self._update_observer = observer

    def _resolve_state(self, message: Message) -> Any:
        if self._state_resolver is None:
            return self._state

        return self._state_resolver(message)

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
        self._kill_event.clear()

        if self._worker_thread is None:
            self._worker_thread = self._transport.spawn(
                target=self._worker,
                name=f'_worker_{self.name}',
                daemon=True,
            )

            self._worker_thread.start()
            self._status = ComponentStatus.RUNNING

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

        Threads are stopped one at a time: the source first, then the worker
        once the source has terminated. The worker consumes the messages left
        in the input queue before exiting, so all the messages received before
        the stop call are processed, and stop() waits for an ``update()`` call
        in progress to return, however long it takes.

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

        self._wake_worker()

    def kill(self):
        """
        Stop the node without processing pending data. All threads are
        signalled at once and exit as soon as their current iteration is
        over: any message still in the input queue is discarded. Messages a
        node keeps in its state are left there. Subclass cleanup in ``stop()``
        still runs.

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
        ]:
            if (
                _t is not None
                and _t.is_alive()
                and not self._transport.is_current(_t)
            ):
                _t.join(timeout=jt.meta.JUTURNA_THREAD_JOIN_TIMEOUT)

    def configure(self): ...

    def update(self, message: Message[T_Input], **kwargs):
        """
        Process a message. Override this method in your custom node class.

        Messages are delivered one at a time, in the order they reach the input
        queue, whatever node sent them (``message.creator`` tells which). A
        node that needs several messages before producing an output, for
        example to join the outputs of more upstream nodes, keeps the pending
        ones in ``kwargs['state']``, and removes them once they are used.

        Parameters
        ----------
        message : Message
            The message received from an upstream node.
        kwargs : dict
            ``state`` is the ``State`` the pipeline keeps for the node across
            messages.

        """
        ...

    def set_on_config(self, prop: str, value: Any): ...

    def warmup(self): ...

    def destroy(self): ...

    def _wake_worker(self):
        with contextlib.suppress(jt.transport.Full):
            self._queue.put_nowait(_WAKE)

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

        self._process(message)

    def _process(self, message: Message):
        self._last_data_source_evt_id = message.id
        error = None

        try:
            state = self._resolve_state(message)

            if state is Node.SKIP_UPDATE:
                return

            self.update(message, state=state)
        except Exception as e:
            error = e
            self._update_failures += 1
            self._last_failure_at = time.time()
            self.logger.error(
                f'unhandled exception in update() '
                f'(failure {self._update_failures}), '
                f'for message id {getattr(message, "id", "?")}',
                exc_info=True,
            )

        if self._update_observer is None:
            return

        try:
            self._update_observer(message, error)
        except Exception:
            self.logger.error(
                f'update observer failed for message id {message.id}',
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
