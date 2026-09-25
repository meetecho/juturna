from collections.abc import Callable
from typing import Any
from typing import Protocol


class Empty(Exception):
    """Raised by Queue.get() when no item is available within the timeout."""


class Queue(Protocol):
    """A FIFO channel used to move messages between nodes and workers."""

    def put(self, item: Any, timeout: float | None = None) -> None: ...

    def get(self, timeout: float | None = None) -> Any: ...

    def get_nowait(self) -> Any: ...

    def empty(self) -> bool: ...

    def full(self) -> bool: ...

    def qsize(self) -> int: ...


class Signal(Protocol):
    """A boolean flag shared across workers, used to signal stop conditions."""

    def set(self) -> None: ...

    def clear(self) -> None: ...

    def is_set(self) -> bool: ...

    def wait(self, timeout: float | None = None) -> bool: ...


class Lock(Protocol):
    """A mutual exclusion primitive, used as a context manager."""

    def __enter__(self) -> None: ...

    def __exit__(self, *args) -> None: ...


class Condition(Protocol):
    """A lock with wait/notify semantics, used to track pending work."""

    def __enter__(self) -> None: ...

    def __exit__(self, *args) -> None: ...

    def wait_for(
        self, predicate: Callable[[], bool], timeout: float | None = None
    ) -> None: ...

    def notify_all(self) -> None: ...


class WorkerHandle(Protocol):
    """A handle to a unit of concurrent execution spawned by a backend."""

    def start(self) -> None: ...

    def join(self, timeout: float | None = None) -> None: ...

    def is_alive(self) -> bool: ...


class TransportBackend(Protocol):
    """
    Factory of concurrency primitives used by nodes and buffers.

    An implementation decides how messages are moved and how workers are
    executed (e.g. real OS threads, or a cooperative scheduler); nodes and
    buffers only depend on this interface, never on the concrete primitives.
    """

    def new_queue(self, maxsize: int = 0) -> Queue: ...

    def new_signal(self) -> Signal: ...

    def new_lock(self) -> Lock: ...

    def new_condition(self) -> Condition: ...

    def spawn(
        self, target: Callable[[], None], name: str, daemon: bool = True
    ) -> WorkerHandle: ...

    def is_current(self, handle: WorkerHandle) -> bool: ...
