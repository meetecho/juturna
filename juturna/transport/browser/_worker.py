import contextvars
import logging

from collections.abc import Callable
from typing import TYPE_CHECKING

from juturna.transport.browser._js import _require_stack_switching
from juturna.transport.browser._queue import _BrowserQueue
from juturna.transport.browser._queue import QueueClosed

if TYPE_CHECKING:
    from juturna.transport.browser._transport import BrowserTransport

# there is no thread identity under JSPI: is_current() reads this instead
_current_worker: contextvars.ContextVar = contextvars.ContextVar(
    '_current_worker', default=None
)


def _get_js_spawn_fn():
    """Build the JS helper that starts a task with stack switching"""
    from js import Function

    return Function.new(
        'pyCallableProxy',
        'return pyCallableProxy.callPromising();',
    )


class _BrowserWorker:
    """
    `WorkerHandle` of `BrowserTransport.spawn()`: a cooperative task started
    with `.callPromising()`. A target that raises is logged, never re-raised
    into `join()`, like `threading.Thread`.
    """

    def __init__(
        self, target: Callable[[], None], name: str, daemon: bool = True
    ):
        self._target = target
        self.name = name
        self.daemon = daemon
        self._done = False
        self._proxy = None
        self._promise = None

    def start(self) -> None:
        from pyodide.ffi import create_proxy

        handle = self

        def wrapped():
            token = _current_worker.set(handle)
            try:
                handle._target()
            except BaseException:
                import traceback

                traceback.print_exc()
            finally:
                _current_worker.reset(token)
                handle._done = True
                proxy.destroy()

        proxy = create_proxy(wrapped)
        self._proxy = proxy
        js_spawn = _get_js_spawn_fn()
        self._promise = js_spawn(proxy)

    def join(self, timeout: float | None = None) -> None:
        from pyodide.ffi import run_sync

        if self._promise is None or self._done:
            return

        _require_stack_switching('_BrowserWorker.join()')

        if timeout is None:
            run_sync(self._promise)
            return

        from js import Function

        # a timed-out join returns without raising, like Thread.join()
        race = Function.new(
            'promise',
            'timeoutMs',
            'return Promise.race(['
            'promise, '
            'new Promise((resolve) => setTimeout(resolve, timeoutMs)),'
            ']);',
        )
        run_sync(race(self._promise, timeout * 1000))

    def is_alive(self) -> bool:
        return self._promise is not None and not self._done


class _BrowserRemoteDestination:
    """
    Stands for a node that runs in another Worker: `put()` writes to the
    inbound queue of that node, which is attached to on first use.
    """

    def __init__(self, transport: 'BrowserTransport', node_name: str):
        self._transport = transport
        self._node_name = node_name
        self._queue: _BrowserQueue | None = None
        self.dropped = 0

    def reset(self) -> None:
        """Forget the queue: the next write attaches to the current one."""
        self._queue = None

    def put(self, message) -> None:
        if self._queue is None:
            self._queue = self._transport._attach_remote(self._node_name)

        try:
            self._queue.put(message)
        except QueueClosed:
            # the node is gone: drop the message, so that the other
            # destinations of the sender still get it
            self.dropped += 1

            if self.dropped == 1:
                logging.getLogger('jt.transport').warning(
                    f'node {self._node_name} of another Worker is gone, '
                    'dropping its messages'
                )
