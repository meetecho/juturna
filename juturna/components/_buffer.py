import typing
import threading
import queue

from juturna.components import Message
from juturna.utils.log_utils import jt_logger

from juturna.payloads._payloads import Batch
from juturna.components._synchronisation_policy import SynchronisationPolicy


class Buffer:
    def __init__(
        self, creator: str, sync_policy: SynchronisationPolicy | None = None
    ):
        self._data = dict()
        self._data_lock = threading.Lock()
        self._policy: SynchronisationPolicy = sync_policy

        # out queue can be built based on the synchronisation policy
        self._out_queue = queue.LifoQueue()

        self._logger = jt_logger(creator)
        self._logger.propagate = True

    def get(self) -> typing.Any:
        return self._out_queue.get()

    def put(self, message: Message):
        self._logger.info('message received, doing nothing')

        if message.creator not in self._data:
            self._data[message.creator] = list()

        self._data[message.creator].append(message)

        with self._data_lock:
            next_batch = self._policy.next_batch(self._data)

            self._consume(next_batch)

    def _consume(self, marks: dict):
        """
        Consume sent data

        Once a policy produces the data marks to send, consume then so that
        local data will be updated accordingly.

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
