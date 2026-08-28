import threading
import queue

from collections.abc import Callable
from typing import Any

from juturna.transport._base import Empty
from juturna.transport._base import WorkerHandle


class _ThreadQueue:
    """Queue primitive backed by queue.Queue."""

    def __init__(self, maxsize: int = 0):
        self._queue = queue.Queue(maxsize=maxsize)

    def put(self, item: Any) -> None:
        self._queue.put(item)

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


class _ThreadSignal:
    """Signal primitive backed by threading.Event."""

    def __init__(self):
        self._event = threading.Event()

    def set(self) -> None:
        self._event.set()

    def clear(self) -> None:
        self._event.clear()

    def is_set(self) -> bool:
        return self._event.is_set()


class _ThreadLock:
    """Lock primitive backed by threading.Lock."""

    def __init__(self):
        self._lock = threading.Lock()

    def __enter__(self) -> None:
        self._lock.acquire()

    def __exit__(self, *args) -> None:
        self._lock.release()


class _ThreadCondition:
    """Condition primitive backed by threading.Condition."""

    def __init__(self):
        self._condition = threading.Condition()

    def __enter__(self) -> None:
        self._condition.acquire()

    def __exit__(self, *args) -> None:
        self._condition.release()

    def wait_for(self, predicate: Callable[[], bool]) -> None:
        self._condition.wait_for(predicate)

    def notify_all(self) -> None:
        self._condition.notify_all()


class _ThreadWorker:
    """Worker handle backed by threading.Thread."""

    def __init__(
        self, target: Callable[[], None], name: str, daemon: bool = True
    ):
        self._thread = threading.Thread(target=target, name=name, daemon=daemon)

    def start(self) -> None:
        self._thread.start()

    def join(self, timeout: float | None = None) -> None:
        self._thread.join(timeout=timeout)

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    @property
    def native_thread(self) -> threading.Thread:
        return self._thread


class ThreadingTransport:
    """
    Default transport backend, based on real OS threads.

    This backend preserves the current concurrency model of `Node` and
    `Buffer`: every worker runs on its own `threading.Thread`, and queues
    are backed by `queue.Queue`.
    """

    def new_queue(self, maxsize: int = 0) -> _ThreadQueue:
        return _ThreadQueue(maxsize)

    def new_signal(self) -> _ThreadSignal:
        return _ThreadSignal()

    def new_lock(self) -> _ThreadLock:
        return _ThreadLock()

    def new_condition(self) -> _ThreadCondition:
        return _ThreadCondition()

    def spawn(
        self, target: Callable[[], None], name: str, daemon: bool = True
    ) -> _ThreadWorker:
        return _ThreadWorker(target, name, daemon)

    def is_current(self, handle: WorkerHandle) -> bool:
        if not isinstance(handle, _ThreadWorker):
            return False

        return threading.current_thread() is handle.native_thread
