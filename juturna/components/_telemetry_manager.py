import threading
import queue
import csv

from juturna.utils.log_utils import jt_logger
from juturna.payloads import ControlSignal


class TelemetryManager:
    def __init__(self, target: str):
        self._target = target

        self._queue = queue.SimpleQueue()
        self._evt = threading.Event()
        self._logger = jt_logger('telemetry')

        self._thread: threading.Thread | None = None

    def start(self):
        if self._thread is not None:
            self._logger.info('telemetry already running')

        self._thread = threading.Thread(
            target=self._read_telemetry,
            args=(),
            daemon=True,
        )

        self._thread.start()

    def stop(self):
        if self._thread is None or self._thread._is_stopped:
            return

        self._queue.put(ControlSignal.STOP)
        self._evt.set()
        self._thread.join()

    def record_telemetry(self, record_batch: list):
        self._queue.put(record_batch)

    def _read_telemetry(self):
        self._logger.info(f'telemetry started, writing on {self._target}')

        _telemetry_lock = threading.Lock()

        with open(self._target, 'a', newline='', buffering=1) as f:
            _writer = csv.writer(f)
            _writer.writerow(
                ['ts', 'evt', 'node', 'origin', 'msg_id', 'src_id', 'size']
            )

            while self._evt:
                telemetry_batch = self._queue.get()

                if telemetry_batch == ControlSignal.STOP:
                    self._evt.set()

                    return

                for entry in telemetry_batch:
                    ts, evt_type, node, origin, msg_id, src_id, size = entry

                    with _telemetry_lock:
                        _writer.writerow(entry)
