import typing
import threading
import queue

from collections.abc import Callable

from juturna.components import Message
from juturna.utils.log_utils import jt_logger

from juturna.payloads._payloads import Batch
from juturna.meta import JUTURNA_MAX_QUEUE_SIZE


class Buffer:
    def __init__(self, creator: str, synchroniser: Callable | None = None):
        self._data: dict[str, list[Message]] = dict()
        self._data_lock = threading.Lock()
        self._synchroniser: Callable = synchroniser

        # out queue can be built based on the synchronisation policy
        self._out_queue = queue.Queue(maxsize=JUTURNA_MAX_QUEUE_SIZE)

        self._logger = jt_logger(creator)
        self._logger.propagate = True

    def get(self) -> typing.Any:
        return self._out_queue.get()

    def put(self, message: Message):
        self._logger.debug('message received in buffer')
        if message.creator not in self._data:
            self._data[message.creator] = list()

        self._data[message.creator].append(message)

        with self._data_lock:
            next_batch = self._synchroniser(self._data)

            self._consume(next_batch)

    def _consume(self, marks: dict):
        """
        Consume sent data

        Once a policy produces the data marks to send, consume then so that
        local data will be updated accordingly. Depending on whether the next
        batch is a single message or a list of messages, the method will write
        in the queue a Message or a Batch object.

        Parameters
        ----------
        marks: dict
            A dictionary of indexes of messages to send for every source.

        """
        to_send = list()

        for mark in marks:
            for pop_idx in marks[mark][::-1]:
                to_send.append(self._data[mark].pop(pop_idx))

        if len(to_send) == 1:
            self._out_queue.put(to_send[0])

            return

        self._out_queue.put(Batch(messages=to_send))

    def flush(self):
        """
        Flush the buffer content
        """
        with self._data_lock:
            self._data = dict()
            while not self._out_queue.empty():
                try:
                    self._out_queue.get_nowait()
                except queue.Empty:
                    break
            self._logger.debug('buffer flushed')
