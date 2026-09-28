from collections.abc import Callable
from contextlib import AbstractContextManager
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


class Event(Protocol):
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

    def new_queue(self, maxsize: int = 0, local: bool = False) -> Queue:
        """
        Build a queue. ``local`` is a hint: the queue is only used within the
        execution context that creates it (the messages never go to another
        worker), so a backend may use a cheaper implementation. A backend whose
        queues are all local anyway ignores it.
        """
        ...

    def node_scope(self, shared: bool) -> AbstractContextManager:
        """
        Return a context manager around the construction of a node. ``shared``
        tells whether the node is written to from another worker, which a
        backend may use to build the queues of the node accordingly. A backend
        with a single kind of queue returns a no-op context manager.
        """
        ...

    def remote_destination(self, node_name: str) -> Any:
        """
        Return the object that stands for a node of another worker: anything
        with a ``put(message)`` method, to be used as a destination of the
        local nodes. Raises ``ValueError`` if the backend cannot reach other
        workers.
        """
        ...

    def new_event(self) -> Event: ...

    def new_lock(self) -> Lock: ...

    def new_condition(self) -> Condition: ...

    def spawn(
        self, target: Callable[[], None], name: str, daemon: bool = True
    ) -> WorkerHandle: ...

    def is_current(self, handle: WorkerHandle) -> bool: ...
