from collections.abc import Callable
from typing import ClassVar

from juturna.telemetry._base import TelemetryContext
from juturna.telemetry.memory._telemetry import DEFAULT_MAX_RECORDS
from juturna.telemetry.memory._telemetry import MemoryTelemetry


class BrowserTelemetry(MemoryTelemetry):
    """Keep the latest records and post each batch to the page"""

    requires: ClassVar[frozenset[str]] = frozenset({'page_channel'})

    def __init__(
        self,
        ctx: TelemetryContext,
        max_records: int = DEFAULT_MAX_RECORDS,
        post: Callable[[dict], None] | None = None,
    ):
        """
        Parameters
        ----------
        ctx : TelemetryContext
            The context of the pipeline.
        max_records : int
            Records kept for `records()`; the oldest are dropped first.
        post : Callable[[dict], None] | None
            Delivers a ``{type, worker, records}`` message to the page.
            Defaults to `postMessage`, which only exists inside a Worker.

        """
        super().__init__(ctx, max_records)

        if post is not None and not callable(post):
            raise ValueError(f'post must be callable, got {post!r}')

        self._post = post or _post_to_page

        # approximate, like `dropped` in the csv manager
        self.post_failures = 0

    def record_telemetry(self, record_batch: list[tuple]):
        """Store a batch and post it to the page"""
        batch = self._store(record_batch)

        if not batch:
            return

        try:
            self._post(
                {'type': 'telemetry', 'worker': self._worker, 'records': batch}
            )
        except Exception:
            # telemetry must never take a node down; the same failure would
            # repeat at every batch, so only the first one is logged
            self.post_failures += 1

            if self.post_failures == 1:
                self._logger.error('cannot post telemetry', exc_info=True)


def _post_to_page(message: dict):
    # js and pyodide only exist inside Pyodide
    from js import Object
    from js import postMessage
    from pyodide.ffi import to_js

    postMessage(to_js(message, dict_converter=Object.fromEntries))
