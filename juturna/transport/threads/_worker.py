import threading

from collections.abc import Callable


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
    def name(self) -> str:
        return self._thread.name

    @property
    def native_thread(self) -> threading.Thread:
        return self._thread
