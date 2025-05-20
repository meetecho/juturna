import threading
import weakref
import logging

from typing import Callable
from typing import Union

from juturna.components._buffer import Buffer
from juturna.components._message import Message


class Bridge:
    def __init__(self, bridge_id: str):
        self.bridge_id = bridge_id

        self._sleep = 0
        self._mode = None
        self._source_f = None

        self._destination_containers = list()
        self._destination_callbacks = list()

        self._update_callback = None
        self._thread = None
        self._stop_event = threading.Event()

    def set_source(self, source: Union[Callable, Buffer],
                   by: int = 0,
                   mode: str = 'post'):
        self._source_f = source
        self._sleep = by
        self._mode = mode

    def unset_source(self):
        self._source_f = None

    @property
    def source(self) -> Union[Callable, Buffer, None]:
        return self._source_f

    @source.setter
    def source(self, src):
        logging.warning(
            f'{self.bridge_id}: use set_source method to set bridge source')

    def add_destination(self, destination: Union[Callable, Buffer]):
        if isinstance(destination, Buffer):
            # self._destination_containers.append(destination)
            self._destination_containers.append(weakref.ref(destination))
        elif isinstance(destination, Callable):
            # self._destination_callbacks.append(destination)
            self._destination_callbacks.append(weakref.ref(destination))
        else:
            raise TypeError('Destination must be Buffer or Callable')

    def on_update_received(self, callback: Callable):
        self._update_callback = callback

    def transmit(self, message: Message):
        for _destination_container in self._destination_containers:
            _destination_container().update(message)

        for _destination_callback in self._destination_callbacks:
            _destination_callback()(message)

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
        #             logging.warning(
        #                 f'{self.bridge_id} thread could not be stopped, wt')
        #             time.sleep(0.1)
        #
        #     self._thread = None

        self._thread = None

    def _worker(self):
        raise NotImplementedError
