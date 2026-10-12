import queue

from typing import Any

from juturna.transport._base import Empty
from juturna.transport._base import Full


class _ThreadQueue:
    """Queue primitive backed by queue.Queue."""

    # NOTE: blocked consumers are currently woken up on stop by putting a
    # sentinel on the queue (see Node._wake_worker). If the minimum supported
    # Python version moves to 3.13+, queue.Queue.shutdown() can replace that:
    # after shutdown, a blocked get() raises queue.ShutDown once the queue is
    # drained, and further put() calls are rejected.
    def __init__(self, maxsize: int = 0):
        self._queue = queue.Queue(maxsize=maxsize)

    def put(self, item: Any, timeout: float | None = None) -> None:
        try:
            self._queue.put(item, timeout=timeout)
        except queue.Full as exc:
            raise Full from exc

    def put_nowait(self, item: Any) -> None:
        try:
            self._queue.put_nowait(item)
        except queue.Full as exc:
            raise Full from exc

    def get(self, timeout: float | None = None) -> Any:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty as exc:
            raise Empty from exc

    def get_nowait(self) -> Any:
        try:
            return self._queue.get_nowait()
        except queue.Empty as exc:
            raise Empty from exc

    def empty(self) -> bool:
        return self._queue.empty()

    def full(self) -> bool:
        return self._queue.full()

    def qsize(self) -> int:
        return self._queue.qsize()
