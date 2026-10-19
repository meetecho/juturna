import contextlib
import threading

from collections.abc import Callable
from typing import Any
from typing import ClassVar

from juturna.transport._base import WorkerHandle

from juturna.transport.threads._queue import _ThreadQueue
from juturna.transport.threads._worker import _ThreadWorker
from juturna.transport.threads._primitives import _ThreadEvent
from juturna.transport.threads._primitives import _ThreadLock
from juturna.transport.threads._primitives import _ThreadCondition


class ThreadingTransport:
    """
    Default transport backend, based on real OS threads.

    This backend preserves the current concurrency model of `Node` and
    `Buffer`: every worker runs on its own `threading.Thread`, and queues
    are backed by `queue.Queue`.
    """

    capabilities: ClassVar[frozenset[str]] = frozenset({'shared_fs'})

    def new_queue(self, maxsize: int = 0, local: bool = False) -> _ThreadQueue:
        # threads share memory: every queue is local already
        return _ThreadQueue(maxsize)

    def node_scope(self, shared: bool) -> contextlib.AbstractContextManager:
        return contextlib.nullcontext()

    def remote_destination(self, node_name: str) -> Any:
        raise ValueError(
            f'node {node_name} runs in another worker, which the '
            f'{type(self).__name__} transport cannot reach'
        )

    def new_event(self) -> _ThreadEvent:
        return _ThreadEvent()

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
