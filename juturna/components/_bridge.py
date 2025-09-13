import threading
import weakref

from collections.abc import Callable

from juturna.components._buffer import Buffer
from juturna.components._message import Message

from juturna.utils.log_utils import jt_logger


_logger = jt_logger()


class Bridge:
    def __init__(self, bridge_id: str):
        self.bridge_id = bridge_id

        self._sleep = 0
        self._mode = None
        self._source_f = None

        self._destination_containers = list()

        self._update_callback = None
        self._thread = None
        self._stop_event = threading.Event()

    def set_source(self, source: Callable | Buffer,
                   by: int = 0,
                   mode: str = 'post'):
        if isinstance(source, Buffer):
            source.subscribe(self._on_buffer_update)
            self._source_f = source.name
        elif isinstance(source, Callable):
            self._source_f = source
            self._sleep = by
            self._mode = mode

    def unset_source(self):
        self._source_f = None

    @property
    def source(self) -> Callable | str | None:
        return self._source_f

    @source.setter
    def source(self, src):
        _logger.warning(
            f'{self.bridge_id}: use set_source method to set bridge source')

    def add_destination(self, destination: Buffer):
        self._destination_containers.append(weakref.ref(destination))

    def on_update_received(self, callback: Callable):
        self._update_callback = callback

    def transmit(self, message: Message):
        for _destination_container in self._destination_containers:
            _destination_container().update(message)

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(
                name=f'_thread_{self.bridge_id}',
                target=self._worker,
                args=(),
                daemon=True)

        self._thread.start()

    def stop(self):
        self._stop_event.set()

        # this code may hang if there are issues with the thread;
        # disable if things get stuck
        # if self._thread and self._thread.is_alive():
        #     while self._thread.is_alive():
        #         try:
        #             self._thread.join()
        #         except RuntimeError as e:
        #             _logger.warning(
        #                 f'{self.bridge_id} thread could not be stopped, wt')
        #             time.sleep(0.1)
        #
        #     self._thread = None

        self._thread = None

    def _on_buffer_update(self, message: Message):
        raise NotImplementedError

    def _worker(self):
        raise NotImplementedError
