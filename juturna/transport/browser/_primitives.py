from collections.abc import Callable

from juturna.transport.browser._js import _atomics_wait_async
from juturna.transport.browser._js import _require_stack_switching
from juturna.transport.browser._js import _now_ms


class _BrowserEvent:
    """Event primitive backed by a single Int32 cell in a SharedArrayBuffer."""

    _CELL = 0

    def __init__(self):
        from js import Int32Array
        from js import SharedArrayBuffer

        sab = SharedArrayBuffer.new(4)
        self._cell = Int32Array.new(sab)

    def set(self) -> None:
        from js import Atomics

        Atomics.store(self._cell, self._CELL, 1)
        Atomics.notify(self._cell, self._CELL)

    def clear(self) -> None:
        from js import Atomics

        Atomics.store(self._cell, self._CELL, 0)

    def is_set(self) -> bool:
        from js import Atomics

        return bool(Atomics.load(self._cell, self._CELL))

    def wait(self, timeout: float | None = None) -> bool:
        deadline = None if timeout is None else _now_ms() + timeout * 1000

        while True:
            if self.is_set():
                return True

            if deadline is not None:
                remaining_ms = deadline - _now_ms()
                if remaining_ms <= 0:
                    return False
                _atomics_wait_async(self._cell, self._CELL, 0, remaining_ms)
            else:
                _atomics_wait_async(self._cell, self._CELL, 0)


class _BrowserLock:
    """
    Mutual exclusion on an Int32 cell. Not reentrant: `Node` and `Buffer`
    never nest acquisitions.
    """

    _CELL = 0

    def __init__(self):
        from js import Int32Array
        from js import SharedArrayBuffer

        sab = SharedArrayBuffer.new(4)
        self._cell = Int32Array.new(sab)

    def __enter__(self) -> None:
        from js import Atomics

        while True:
            prev = int(Atomics.compareExchange(self._cell, self._CELL, 0, 1))

            if prev == 0:
                return

            _atomics_wait_async(self._cell, self._CELL, 1)

    def __exit__(self, *exc_info) -> None:
        from js import Atomics

        Atomics.store(self._cell, self._CELL, 0)
        Atomics.notify(self._cell, self._CELL, 1)


class _BrowserCondition:
    """Condition variable: a generation counter plus a `_BrowserLock`"""

    _GEN = 0

    def __init__(self):
        from js import Int32Array
        from js import SharedArrayBuffer

        sab = SharedArrayBuffer.new(4)
        self._gen_cell = Int32Array.new(sab)
        self._lock = _BrowserLock()

    def __enter__(self) -> None:
        self._lock.__enter__()

    def __exit__(self, *exc_info) -> None:
        self._lock.__exit__(*exc_info)

    def wait_for(
        self, predicate: Callable[[], bool], timeout: float | None = None
    ) -> None:
        from js import Atomics

        if predicate():
            return

        # checked before the lock is released: a raise from the wait would
        # leave the lock released, and the enclosing `with` would release it
        # again
        _require_stack_switching('_BrowserCondition.wait_for()')

        # one deadline for the whole call, like threading.Condition
        deadline = None if timeout is None else _now_ms() + timeout * 1000

        while not predicate():
            remaining_ms = None
            if deadline is not None:
                remaining_ms = deadline - _now_ms()
                if remaining_ms <= 0:
                    return

            # read before the lock is released: a notify in between makes
            # the wait return at once instead of being missed
            gen = int(Atomics.load(self._gen_cell, self._GEN))
            self._lock.__exit__(None, None, None)
            _atomics_wait_async(self._gen_cell, self._GEN, gen, remaining_ms)
            self._lock.__enter__()

    def notify_all(self) -> None:
        from js import Atomics

        Atomics.add(self._gen_cell, self._GEN, 1)
        Atomics.notify(self._gen_cell, self._GEN)
