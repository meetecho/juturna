import pathlib
import inspect
import string
import logging
import threading
import queue
import time

from collections.abc import Callable

from typing import Any

from juturna.components import Message
from juturna.payloads import ControlPayload
from juturna.payloads import ControlSignal

from juturna.names import ComponentStatus
from juturna.utils.log_utils import jt_logger

from juturna.meta import JUTURNA_THREAD_JOIN_TIMEOUT
from juturna.meta import JUTURNA_MAX_QUEUE_SIZE
from juturna.meta import JUTURNA_TELEMETRY_BATCH_SIZE

from juturna.components._buffer import Buffer
from juturna.components._telemetry_manager import TelemetryManager
from juturna.components._synchronisers import _SYNCHRONISERS


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

        """
        self._name = node_name
        self._status: ComponentStatus | None = None
        self._session_id: str | None = None
        self._pipe_path: str | None = None
        self._pipe_name: str | None = pipe_name

        self.pipe_id: str | None = None

        _logger_name = f'{self.pipe_name}.{self._name}'
        self._logger = jt_logger(_logger_name)
        self._logger.propagate = True

        self._queue = queue.Queue(maxsize=JUTURNA_MAX_QUEUE_SIZE)
        self._worker_thread: threading.Thread | None = None
        self._source_thread: threading.Thread | None = None
        self._update_thread: threading.Thread | None = None

        self._stop_worker_event = threading.Event()
        self._stop_source_event = threading.Event()
        self._stop_update_event = threading.Event()

        self._suspended = False
        self._auto_dump = False

        # buffer stores messages, policy manages them
        # if the synchroniser is not provided, get local one or default
        self._synchroniser = synchroniser or (
            self.next_batch
            if hasattr(self, 'next_batch')
            else _SYNCHRONISERS['passthrough']
        )

        self._buffer = Buffer(_logger_name, self._synchroniser)

        self._source_f: Callable | None = None
        self._source_sleep = -1
        self._source_mode = ''

        self._destinations: dict[str, Node] = dict()
        self._origins: list = list()
        self._last_data_source_evt_id: int | None = None

        self._telemetry_buffer = list()
        self._telemetry_manager: TelemetryManager | None = None

    def __del__(self): ...

    @property
    def name(self) -> str | None:
        """The node symbolic name"""
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name

    @property
    def status(self) -> ComponentStatus | None:
        return self._status

    @property
    def configuration(self) -> dict:
        return {'name': self.name, 'session_id': self.pipe_id}

    @status.setter
    def status(self, new_status: ComponentStatus):
        self._status = ComponentStatus(new_status)

    @property
    def pipe_name(self) -> str | None:
        """
        Id of the pipe the node belongs to. This will automatically be
        assigned to the node when it is intantiated within a pipeline, but can
        also be set manually. An isolated node not included within a pipeline
        will have a ``None`` value for this field.
        """
        return self._pipe_name

    @pipe_name.setter
    def pipe_name(self, pipe_name: str):
        self._pipe_name = pipe_name

    @property
    def pipe_path(self) -> str | None:
        """
        Path to the pipeline session directory. The node has a dedicated folder
        within the pipeline session directory where it stores its data. This
        will automatically be assigned to the node when it is intantiated within
        a pipeline, but can also be set manually. An isolated node not included
        within a pipeline will have a ``None`` value for this field.
        """
        return self._pipe_path

    @pipe_path.setter
    def pipe_path(self, session_path: str):
        self._pipe_path = session_path

    @property
    def static_path(self) -> pathlib.Path:
        """
        Path to the directory where the node is defined. This is useful for
        storing static files (e.g. configuration files) that are needed by the
        node.
        """
        return pathlib.Path(inspect.getfile(self.__class__)).parent

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def synchroniser(self) -> Callable:
        return self._synchroniser

    @synchroniser.setter
    def synchroniser(self, synchroniser: Callable):
        self.synchroniser = synchroniser

    @property
    def origins(self) -> list:
        return self._origins

    @property
    def destinations(self) -> list:
        return list(self._destinations.keys())

    def link_telemetry(self, manager: TelemetryManager):
        self._telemetry_manager = manager

    def put(self, message: Message | ControlSignal):
        self._queue.put(message)

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
            self._logger.warning('message cannot be dumped')

        return str(dump_path)

    def set_source(self, source: Callable, by: int = 0, mode: str = 'post'):
        """
        Set the node source (to be used for ``source`` nodes). The source can be
        either a callable or a buffer. However, source nodes are expected to be
        provided with a callable that will be used to generate the data to be
        transmitted.

        Parameters
        ----------
        source : Union[Buffer, callable]
            The source to be set. This can be either a buffer or a callable.
        by : int, optional
            The time interval (in seconds) between two consecutive calls to the
            source. This parameter is only used if the source is a callable.
            The default is 0.
        mode : str, optional
            Whether to apply the ``by`` timer before or after the source call.
            The default is ``post``, indicating the source function will wait
            for ``by`` seconds before being called. If set to ``pre``, the
            source function will be called and then wait for ``by`` seconds
            before being called again.

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

    def transmit(self, message: Message[T_Output] | ControlSignal):
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
        if self._worker_thread is None:
            self._worker_thread = threading.Thread(
                name=f'_worker_{self.name}',
                target=self._worker,
                args=(),
                daemon=True,
            )

            self._worker_thread.start()
            self._status = ComponentStatus.RUNNING

        if self._update_thread is None:
            self._update_thread = threading.Thread(
                name=f'_update_{self.name}',
                target=self._update,
                args=(),
                daemon=True,
            )

            self._update_thread.start()

        if self._source_f is None:
            return

        if self._source_thread is None:
            self._source_thread = threading.Thread(
                name=f'_source_{self.name}',
                target=self._source,
                args=(),
                daemon=True,
            )

            self._source_thread.start()

    def stop(self):
        """
        Stop the node and begin processing. This method is called automatically
        when the parent pipeline is stopped. If you override this method in
        your custom node class, make sure to call the parent method to ensure
        the node is stopped correctly.
        """
        if self._status == ComponentStatus.STOPPED:
            return

        self._stop_worker_event.set()
        self._stop_source_event.set()
        self._stop_update_event.set()

        self._queue.put(None)
        self._buffer.put(None)

        for _t in [
            self._source_thread,
            self._worker_thread,
            self._update_thread,
        ]:
            if _t and _t.is_alive:
                _t.join(timeout=JUTURNA_THREAD_JOIN_TIMEOUT)

        self._worker_thread = None
        self._source_thread = None
        self._update_thread = None
        self._status = ComponentStatus.STOPPED

        self._logger.info('node stopped')

    def configure(self): ...

    def update(self, message: Message[T_Input]): ...

    def set_on_config(self, prop: str, value: Any): ...

    def warmup(self): ...

    def destroy(self): ...

    def _worker(self):
        while not self._stop_worker_event.is_set():
            message = self._queue.get()

            if message is None:
                self._stop_worker_event.set()

                continue

            if isinstance(message.payload, ControlPayload):
                if message.payload.signal < 0:
                    self._logger.info('stop signal received')
                    self._stop_worker_event.set()
                    self._buffer.put(None)

                self._handle_control(message)

                continue

            if self._suspended:
                self.transmit(message)

                continue

            self._buffer.put(message)

            if isinstance(message, Message):
                self._rec_telemetry(message, 'rx')

    def _update(self):
        while not self._stop_update_event.is_set():
            batch = self._buffer.get()

            if batch is None:
                self._stop_update_event.set()

                continue

            self._last_data_source_evt_id = batch.id
            self.update(batch)

    def _source(self):
        while not self._stop_source_event.is_set():
            if self._source_mode == 'pre':
                time.sleep(self._source_sleep)

            message = self._source_f()

            if (
                isinstance(message.payload, ControlPayload)
                and message.payload.signal < 0
            ):
                self._stop_source_event.set()
                self.put(message)

                continue

            if self._stop_source_event.is_set():
                return

            if self._source_mode == 'post':
                time.sleep(self._source_sleep)

            self.put(message)

    def _handle_control(self, message: Message):
        _control_thread = threading.Thread(
            target=self._control,
            args=(message,),
            daemon=True,
        )

        _control_thread.start()

    def _control(self, message: Message):
        if message.payload.signal < 0:
            self.stop()

        match message.payload.signal:
            case ControlSignal.STOP_PROPAGATE:
                self.transmit(message)

                return
            case ControlSignal.STOP:
                return
            case ControlSignal.START:
                self.start()

                return
            case ControlSignal.SUSPEND:
                self._suspended = True
                self._logger.info('node suspended')

                return
            case ControlSignal.RESUME:
                self._suspended = False
                self._logger.info('node resumed')

                return
            case None:
                return

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
            message.payload.size_bytes,
        )

        self._telemetry_buffer.append(telemetry_entry)

        if len(self._telemetry_buffer) >= JUTURNA_TELEMETRY_BATCH_SIZE:
            self._telemetry_manager.record_telemetry(self._telemetry_buffer)
            self._telemetry_buffer = list()
