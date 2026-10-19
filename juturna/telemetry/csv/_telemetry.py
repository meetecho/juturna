import contextlib
import csv
import pathlib

from typing import ClassVar

from juturna.meta import JUTURNA_THREAD_JOIN_TIMEOUT
from juturna.telemetry._base import TELEMETRY_FIELDS
from juturna.telemetry._base import TelemetryContext
from juturna.telemetry._base import tag_records
from juturna.transport import Empty
from juturna.transport import Full
from juturna.transport import WorkerHandle
from juturna.utils import jt_utils
from juturna.utils.log_utils import jt_logger

DEFAULT_MAX_PENDING = 10000


class CsvTelemetry:
    """Write the telemetry records on a CSV file, from a worker of its own"""

    requires: ClassVar[frozenset[str]] = frozenset({'shared_fs'})

    def __init__(
        self,
        ctx: TelemetryContext,
        target: str,
        max_pending: int = DEFAULT_MAX_PENDING,
    ):
        """
        Parameters
        ----------
        ctx : TelemetryContext
            The context of the pipeline.
        target : str
            Name of the CSV file, relative to the folder of the pipeline.
        max_pending : int
            Batches waiting to be written. When the writer cannot keep up, the
            new batches are dropped (see `dropped`): the nodes never wait.

        """
        # the target becomes a path under the pipeline folder
        jt_utils.check_name(target, 'telemetry file')

        # a csv extension keeps the target from replacing any other file of
        # the pipeline folder, such as its configuration
        if pathlib.PurePath(target).suffix.lower() != '.csv':
            raise ValueError(
                f'invalid telemetry file name {target!r}: it must end with '
                '".csv"'
            )

        if (
            isinstance(max_pending, bool)
            or not isinstance(max_pending, int)
            or max_pending < 1
        ):
            raise ValueError(
                f'max_pending must be a positive integer, got {max_pending}'
            )

        self._target = pathlib.Path(ctx.pipe_path, target)
        self._worker = ctx.worker
        self._transport = ctx.transport

        # batches are lists, which a cross-worker ring queue does not accept
        self._queue = ctx.transport.new_queue(maxsize=max_pending, local=True)
        self._evt = ctx.transport.new_event()
        self._logger = jt_logger('telemetry')

        self._thread: WorkerHandle | None = None
        self._file = None

        # false from a stop to the next start: what arrives is dropped
        self._open = True

        # approximate: `+=` from several threads may miss a count
        self.dropped = 0

    def start(self):
        """Start the worker that writes the file"""
        if self._thread is not None:
            self._logger.info('telemetry already running')

            return

        # opened here, not by the writer: a target that cannot be written
        # fails the start of the pipeline instead of killing a worker
        self._file = open(self._target, 'a', newline='', buffering=1)  # noqa: SIM115

        try:
            # the header is written once; a file of version 2 has an older one,
            # and the new header tells records() what the new rows look like
            if self._file.tell() == 0 or not self._has_current_header():
                csv.writer(self._file).writerow(TELEMETRY_FIELDS)

            # what a late producer left from the previous run is not data of
            # this one
            if not self._open:
                self._discard_pending()

            self._open = True

            self._thread = self._transport.spawn(
                target=self._read_telemetry,
                name='telemetry',
                daemon=True,
            )

            self._thread.start()
        except BaseException:
            self._file.close()
            self._thread = None

            raise

    def stop(self):
        """Write what is left and stop the worker; later batches are dropped"""
        self._open = False

        if self._thread is not None:
            if self._thread.is_alive():
                self._evt.set()

                # an empty batch wakes up the reader blocked on get(); if the
                # queue is full the reader is busy and sees the event itself
                with contextlib.suppress(Full):
                    self._queue.put_nowait(list())

                self._thread.join()

            # a stopped manager can be started again, as after a failed start
            self._thread = None
            self._evt.clear()

        self._discard_pending()

        if self.dropped:
            self._logger.warning(f'{self.dropped} telemetry records dropped')

    def record_telemetry(self, record_batch: list[tuple]):
        """Queue a batch to be written, or drop it if the writer is behind"""
        if not self._open:
            self.dropped += len(record_batch)

            return

        try:
            self._queue.put_nowait(tag_records(record_batch, self._worker))
        except Full:
            self.dropped += len(record_batch)

    def records(self) -> list[tuple]:
        """The records written so far, parsed, oldest first"""
        try:
            with open(self._target, newline='') as f:
                rows = list(csv.reader(f))
        except FileNotFoundError:
            return []

        # a header says how many fields the rows after it have (the worker is
        # missing in version 2); a row may be partial or corrupted: skipped
        records = []
        width = len(TELEMETRY_FIELDS)

        for row in rows:
            if row and row[0] == 'ts':
                width = len(row)

                continue

            if len(row) != width:
                continue

            try:
                records.append(_parse(row))
            except ValueError:
                continue

        return records

    def _read_telemetry(self):
        self._logger.info(f'telemetry started, writing on {self._target}')

        with self._file as f:
            _writer = csv.writer(f)

            while not self._evt.is_set():
                try:
                    telemetry_batch = self._queue.get(
                        timeout=JUTURNA_THREAD_JOIN_TIMEOUT
                    )
                except Empty:
                    continue

                self._write(_writer, telemetry_batch)

            while True:
                try:
                    telemetry_batch = self._queue.get_nowait()
                except Empty:
                    break

                self._write(_writer, telemetry_batch)

    def _has_current_header(self) -> bool:
        with open(self._target, newline='') as f:
            return next(csv.reader(f), []) == list(TELEMETRY_FIELDS)

    def _discard_pending(self):
        while True:
            try:
                batch = self._queue.get_nowait()
            except Empty:
                break

            self.dropped += len(batch)

    def _write(self, writer, batch: list[tuple]):
        try:
            writer.writerows(batch)
        except Exception:
            # a batch that cannot be written must not kill the writer
            self.dropped += len(batch)
            self._logger.error('cannot write telemetry', exc_info=True)


def _parse(row: list[str]) -> tuple:
    if len(row) not in (len(TELEMETRY_FIELDS) - 1, len(TELEMETRY_FIELDS)):
        raise ValueError(f'a record has 7 or 8 fields, got {len(row)}')

    ts, evt, node, origin, msg_id, src_id, size, *worker = row

    return (
        float(ts),
        evt,
        node,
        origin,
        int(msg_id),
        int(src_id) if src_id else None,
        int(size),
        worker[0] if worker else None,
    )
