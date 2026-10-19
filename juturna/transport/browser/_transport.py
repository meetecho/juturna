"""
Browser transport backend (Pyodide), based on `SharedArrayBuffer` and
`Atomics`, made concurrent by JSPI (JavaScript Promise Integration).

Requirements:

- Pyodide >= 314.0.0, loaded in a module-type Worker through a dynamic
  `import()` of `pyodide.mjs`. Older builds crash on nested
  `callPromising()`.
- The entry point that drives a node (`Node.start()` and what it calls) must
  be invoked from JS with `.callPromising()`. The blocking primitives here
  raise a `RuntimeError` when it is not.

Every `js` and `pyodide.ffi` import is deferred into the methods that need
it, so importing this module works on a desktop interpreter too.

Differences from `ThreadingTransport`:

- a queue slot has a fixed size: `put()` raises `ValueError` for a message
  that does not fit, instead of growing;
- the capacity of a queue is capped by `DEFAULT_QUEUE_CAPACITY`, not by
  `JUTURNA_MAX_QUEUE_SIZE`, which would pre-allocate hundreds of MB at video
  frame sizes;
- `Image`, `Audio` and `Bytes` payloads take a fast binary path, anything
  else is pickled.

A queue is a ring only when its messages can reach another Worker. Those that
never leave it (`Buffer._out_queue`, and the inbound queue of a node that
nothing in another Worker writes to, see `node_scope()`) are
`_BrowserLocalQueue`: the messages stay Python objects, which saves a
serialization and a copy on each side, about 1 ms for a 640x480 RGBA frame.
"""

import contextlib

from collections.abc import Callable
from typing import ClassVar

from juturna.transport._base import WorkerHandle

from juturna.transport.browser._queue import _BrowserQueue
from juturna.transport.browser._queue import _BrowserLocalQueue
from juturna.transport.browser._primitives import _BrowserEvent
from juturna.transport.browser._primitives import _BrowserLock
from juturna.transport.browser._primitives import _BrowserCondition
from juturna.transport.browser._js import _require_stack_switching
from juturna.transport.browser._wire import DEFAULT_QUEUE_CAPACITY
from juturna.transport.browser._wire import DEFAULT_MAX_META_JSON_BYTES
from juturna.transport.browser._wire import DEFAULT_MAX_PAYLOAD_BYTES
from juturna.transport.browser._worker import _current_worker
from juturna.transport.browser._worker import _BrowserWorker
from juturna.transport.browser._worker import _BrowserRemoteDestination


class BrowserTransport:
    """Transport backend for a pipeline running in a browser (Pyodide)"""

    capabilities: ClassVar[frozenset[str]] = frozenset({'page_channel'})

    def __init__(
        self,
        queue_capacity: int = DEFAULT_QUEUE_CAPACITY,
        max_meta_json_bytes: int = DEFAULT_MAX_META_JSON_BYTES,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
        remote_timeout: float = 30.0,
    ):
        """
        `remote_timeout` is how many seconds a write towards another Worker
        waits for its `connect()`.
        """
        self._queue_capacity = queue_capacity
        self._max_meta_json_bytes = max_meta_json_bytes
        self._max_payload_bytes = max_payload_bytes
        self._remote_timeout = remote_timeout

        self._scope_shared: bool | None = None
        self._remote_handles: dict = {}
        self._remote_events: dict = {}
        self._remote_destinations: dict = {}

    @contextlib.contextmanager
    def node_scope(self, shared: bool):
        """
        Declare, for the queues built inside the block, whether the node they
        belong to is written to from another Worker. When it is not, a queue is
        local (see `_BrowserLocalQueue`); outside a block, or with ``shared``
        true, it is a ring.
        """
        previous = self._scope_shared
        self._scope_shared = shared

        try:
            yield
        finally:
            self._scope_shared = previous

    def new_queue(
        self, maxsize: int = 0, local: bool = False
    ) -> _BrowserQueue | _BrowserLocalQueue:
        # every queue of a node written from another Worker is a ring; an
        # unbounded queue (0) has no equivalent, and a larger maxsize is
        # capped to the capacity because it drives the memory pre-allocated
        capacity = (
            self._queue_capacity
            if not maxsize
            else min(maxsize, self._queue_capacity)
        )

        if local or self._scope_shared is False:
            return _BrowserLocalQueue(capacity)

        return _BrowserQueue(
            capacity=capacity,
            max_meta_json_bytes=self._max_meta_json_bytes,
            max_payload_bytes=self._max_payload_bytes,
        )

    def queue_handle(self, queue: _BrowserQueue):
        """What to post to another Worker so it can `attach_queue()`."""
        return queue.handle()

    def attach_queue(self, handle) -> _BrowserQueue:
        """Attach to a queue created in another Worker, from its handle"""
        return _BrowserQueue(
            capacity=handle.capacity,
            max_meta_json_bytes=handle.max_meta_json_bytes,
            max_payload_bytes=handle.max_payload_bytes,
            sab=handle.sab,
        )

    def remote_destination(self, node_name: str) -> _BrowserRemoteDestination:
        """
        The destination standing for a node of another Worker, to be linked
        as if it were the node itself (see `Pipeline.warmup`).
        """
        if node_name not in self._remote_destinations:
            self._remote_destinations[node_name] = _BrowserRemoteDestination(
                self, node_name
            )

        return self._remote_destinations[node_name]

    def connect(self, node_name: str, handle) -> None:
        """
        Register the handle of the inbound queue of a node of another Worker,
        as returned by its `queue_handle()`. Writes to that node's
        destination wait for it. Calling it again for the same node, with the
        handle of a rebuilt node, makes the destination write to the new queue.
        """
        self._remote_handles[node_name] = handle

        # a node that was rebuilt has a new queue: writes must go there
        if node_name in self._remote_destinations:
            self._remote_destinations[node_name].reset()

        self._remote_event(node_name).set()

    def _remote_event(self, node_name: str):
        import asyncio

        if node_name not in self._remote_events:
            self._remote_events[node_name] = asyncio.Event()

        return self._remote_events[node_name]

    def _attach_remote(self, node_name: str) -> _BrowserQueue:
        import asyncio

        from pyodide.ffi import run_sync

        event = self._remote_event(node_name)

        if not event.is_set():
            _require_stack_switching(f'a write to node {node_name}')

            try:
                run_sync(asyncio.wait_for(event.wait(), self._remote_timeout))
            except TimeoutError:
                raise RuntimeError(
                    f'node {node_name} of another Worker was not connected '
                    f'within {self._remote_timeout} seconds'
                ) from None

        return self.attach_queue(self._remote_handles[node_name])

    def new_event(self) -> _BrowserEvent:
        return _BrowserEvent()

    def new_lock(self) -> _BrowserLock:
        return _BrowserLock()

    def new_condition(self) -> _BrowserCondition:
        return _BrowserCondition()

    def spawn(
        self, target: Callable[[], None], name: str, daemon: bool = True
    ) -> _BrowserWorker:
        return _BrowserWorker(target, name, daemon)

    def is_current(self, handle: WorkerHandle) -> bool:
        return _current_worker.get() is handle
