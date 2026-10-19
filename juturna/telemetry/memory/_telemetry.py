from collections import deque
from typing import ClassVar

from juturna.telemetry._base import TelemetryContext
from juturna.telemetry._base import tag_records
from juturna.utils.log_utils import jt_logger

DEFAULT_MAX_RECORDS = 10000
_READ_RETRIES = 3


class MemoryTelemetry:
    """Keep the latest telemetry records in memory"""

    requires: ClassVar[frozenset[str]] = frozenset()

    def __init__(
        self, ctx: TelemetryContext, max_records: int = DEFAULT_MAX_RECORDS
    ):
        """
        Parameters
        ----------
        ctx : TelemetryContext
            The context of the pipeline.
        max_records : int
            Records kept; the oldest are dropped first.

        """
        # bool is an int: `true` in a configuration would mean 1
        if (
            isinstance(max_records, bool)
            or not isinstance(max_records, int)
            or max_records < 1
        ):
            raise ValueError(
                f'max_records must be a positive integer, got {max_records}'
            )

        self._worker = ctx.worker
        self._records: deque[tuple] = deque(maxlen=max_records)

        # false from a stop to the next start: what arrives is dropped
        self._open = True
        self._logger = jt_logger('telemetry')

    def start(self):
        """Accept records again, after a stop"""
        self._open = True

    def stop(self):
        """Drop the records that arrive from now on, keep the ones collected"""
        self._open = False

    def record_telemetry(self, record_batch: list[tuple]):
        """Store a batch of records"""
        self._store(record_batch)

    def records(self) -> list[tuple]:
        """The records kept so far, oldest first"""
        # no lock: a node thread must never wait for a reader, so the reader
        # retries when a writer changes the deque while it is being copied
        # (only possible on a free-threaded build)
        for _ in range(_READ_RETRIES):
            try:
                return list(self._records)
            except RuntimeError:
                self._logger.warning('records changed while being read: retry')

        return list(self._records)

    def _store(self, record_batch: list[tuple]) -> list[tuple]:
        if not self._open or not record_batch:
            return []

        batch = tag_records(record_batch, self._worker)
        self._records.extend(batch)

        return batch
