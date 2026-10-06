import csv

from juturna.utils.log_utils import jt_logger
from juturna.meta import JUTURNA_THREAD_JOIN_TIMEOUT

from juturna.transport import Empty
from juturna.transport import Event
from juturna.transport import ThreadingTransport
from juturna.transport import TransportBackend
from juturna.transport import WorkerHandle


class TelemetryManager:
    def __init__(self, target: str, transport: TransportBackend | None = None):
        self._target = target
        self._transport: TransportBackend = transport or ThreadingTransport()

        self._queue = self._transport.new_queue()
        self._evt: Event = self._transport.new_event()
        self._logger = jt_logger('telemetry')

        self._thread: WorkerHandle | None = None

    def start(self):
        if self._thread is not None:
            self._logger.info('telemetry already running')

            return

        self._thread = self._transport.spawn(
            target=self._read_telemetry,
            name='telemetry',
            daemon=True,
        )

        self._thread.start()

    def stop(self):
        if self._thread is None or not self._thread.is_alive():
            return

        self._evt.set()

        # an empty batch wakes up the reader blocked on get(), and is a no-op
        # when written
        self._queue.put(list())
        self._thread.join()

    def record_telemetry(self, record_batch: list):
        self._queue.put(record_batch)

    def _read_telemetry(self):
        self._logger.info(f'telemetry started, writing on {self._target}')

        with open(self._target, 'a', newline='', buffering=1) as f:
            _writer = csv.writer(f)
            _writer.writerow(
                ['ts', 'evt', 'node', 'origin', 'msg_id', 'src_id', 'size']
            )

            while not self._evt.is_set():
                try:
                    telemetry_batch = self._queue.get(
                        timeout=JUTURNA_THREAD_JOIN_TIMEOUT
                    )
                except Empty:
                    continue

                _writer.writerows(telemetry_batch)

            while True:
                try:
                    telemetry_batch = self._queue.get_nowait()
                except Empty:
                    break

                _writer.writerows(telemetry_batch)
