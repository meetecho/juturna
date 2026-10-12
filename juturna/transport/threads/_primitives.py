import threading

from collections.abc import Callable


class _ThreadEvent:
    """Event primitive backed by threading.Event."""

    def __init__(self):
        self._event = threading.Event()

    def set(self) -> None:
        self._event.set()

    def clear(self) -> None:
        self._event.clear()

    def is_set(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)


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

    def wait_for(
        self, predicate: Callable[[], bool], timeout: float | None = None
    ) -> None:
        self._condition.wait_for(predicate, timeout=timeout)

    def notify_all(self) -> None:
        self._condition.notify_all()
