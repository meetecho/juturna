import threading

import pytest

from juturna.telemetry import TelemetryContext
from juturna.telemetry.memory import MemoryTelemetry
from juturna.transport import ThreadingTransport


def _ctx(worker='w1'):
    return TelemetryContext(ThreadingTransport(), worker, '/tmp')


def _record(i):
    return (float(i), 'tx', 'in', 'in', i, i, 10)


def test_records_are_tagged_with_the_worker_last():
    manager = MemoryTelemetry(_ctx('w1'))

    manager.record_telemetry([_record(0), _record(1)])

    records = manager.records()
    assert len(records) == 2, f'Expected 2 records, got {records}'
    assert records[1][-1] == 'w1', f'The worker must be last, got {records[1]}'
    assert records[1][:-1] == _record(1), f'Unexpected {records[1]}'


def test_oldest_records_are_dropped_beyond_the_limit():
    manager = MemoryTelemetry(_ctx(), max_records=3)

    manager.record_telemetry([_record(i) for i in range(5)])

    ids = [r[4] for r in manager.records()]
    assert ids == [2, 3, 4], f'Expected the latest 3 records, got {ids}'


def test_empty_batch_is_ignored():
    manager = MemoryTelemetry(_ctx())

    manager.record_telemetry([])

    assert manager.records() == [], 'Expected no records'


def test_max_records_must_be_positive():
    with pytest.raises(ValueError, match='max_records'):
        MemoryTelemetry(_ctx(), max_records=0)


def test_concurrent_writers_and_reader():
    manager = MemoryTelemetry(_ctx(), max_records=50)
    errors = []

    def write():
        for i in range(500):
            manager.record_telemetry([_record(i)])

    def read():
        try:
            for _ in range(500):
                manager.records()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=f) for f in (write, write, read)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    assert not errors, f'The reader failed: {errors}'


@pytest.mark.parametrize('max_records', [True, False, 1.5, '5', None])
def test_max_records_must_be_a_real_integer(max_records):
    with pytest.raises(ValueError, match='max_records'):
        MemoryTelemetry(_ctx(), max_records=max_records)


def test_records_after_a_stop_are_dropped_until_the_next_start():
    manager = MemoryTelemetry(_ctx())

    manager.record_telemetry([_record(0)])
    manager.stop()
    manager.record_telemetry([_record(1)])
    manager.start()
    manager.record_telemetry([_record(2)])

    ids = [r[4] for r in manager.records()]
    assert ids == [0, 2], f'Expected the records of the two runs, got {ids}'
