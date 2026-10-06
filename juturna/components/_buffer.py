import typing
import contextlib

from collections.abc import Callable

from juturna.components import Message
from juturna.utils.log_utils import jt_logger

from juturna.payloads import Batch
from juturna.meta import JUTURNA_MAX_QUEUE_SIZE

from juturna.transport import Empty
from juturna.transport import Full
from juturna.transport import ThreadingTransport
from juturna.transport import TransportBackend


class Buffer:
    def __init__(
        self,
        creator: str,
        synchroniser: Callable | None = None,
        transport: TransportBackend | None = None,
    ):
        self._transport: TransportBackend = transport or ThreadingTransport()

        self._data: dict[str, list[Message]] = dict()
        self._data_lock = self._transport.new_lock()
        self._synchroniser: Callable = synchroniser

        self._out_queue = self._transport.new_queue(
            maxsize=JUTURNA_MAX_QUEUE_SIZE, local=True
        )

        self._creator = creator
        self._logger = jt_logger(creator)
        self._logger.propagate = True

    def get(self, timeout: float = None) -> typing.Any:
        return self._out_queue.get(timeout=timeout)

    def get_nowait(self) -> typing.Any:
        return self._out_queue.get_nowait()

    def wake(self, token: typing.Any):
        """
        Wake up a consumer blocked on get() by putting a token in the out
        queue. If the queue is full, the consumer is not blocked and the token
        is not needed, so it is dropped.
        """
        with contextlib.suppress(Full):
            self._out_queue.put_nowait(token)

    def put(self, message: Message | None):
        with self._data_lock:
            self._data.setdefault(message.creator, list()).append(message)

            next_batch = self._synchroniser(self._data)

            self._consume(next_batch)

    def empty(self) -> bool:
        with self._data_lock:
            return (
                all(len(v) == 0 for v in self._data.values())
                and self._out_queue.empty()
            )

    def _consume(self, marks: dict[str, list[int]]):
        """
        Consume sent data

        Once a policy produces the data marks to send, consume then so that
        local data will be updated accordingly. Depending on whether the next
        batch is a single message or a list of messages, the method will write
        in the queue a Message or a Batch object.

        Parameters
        ----------
        marks: dict[str, list[int]]
            A dictionary of indexes of messages to send for every source.

        """
        to_send = list()

        for mark in marks:
            for pop_idx in marks[mark][::-1]:
                to_send.append(self._data[mark].pop(pop_idx))

        if len(to_send) == 0:
            return

        to_send = (
            to_send[0]
            if len(to_send) == 1
            else Message[Batch](
                creator=f'{self._creator}_sync',
                payload=Batch(messages=tuple(to_send)),
            )
        )

        self._out_queue.put(to_send)

    def flush(self):
        """Flush the buffer content"""
        with self._data_lock:
            self._data = dict()

            while not self._out_queue.empty():
                try:
                    self._out_queue.get_nowait()
                except Empty:
                    break

            self._logger.debug('buffer flushed')
