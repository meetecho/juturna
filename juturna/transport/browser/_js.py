def _atomics_wait_async(
    cell, index: int, expected: int, timeout_ms=None
) -> None:
    """
    Cooperative `Atomics.wait()`: suspend only the current task. The loops of
    a node are tasks of one event loop (Pyodide has no threads), so the
    synchronous `Atomics.wait()` would freeze all of them.
    """
    from js import Atomics
    from pyodide.ffi import run_sync

    result = (
        Atomics.waitAsync(cell, index, expected)
        if timeout_ms is None
        else Atomics.waitAsync(cell, index, expected, timeout_ms)
    )

    if result.async_:
        _require_stack_switching('a BrowserTransport wait')
        run_sync(result.value)


def _require_stack_switching(op: str) -> None:
    """Raise a clear error if `op` would block outside `.callPromising()`"""
    from pyodide.ffi import can_run_sync

    if not can_run_sync():
        raise RuntimeError(
            f'{op} would block, but the current call is not running '
            'inside a stack-switching-enabled entry point. Every code '
            'path that can reach a BrowserTransport wait must be invoked '
            'via `<callable>.callPromising()` on Pyodide >= 314.0.0'
        )


def _now_ms() -> float:
    import time

    return time.time() * 1000
