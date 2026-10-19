from unittest import mock

import pytest

from juturna.telemetry import TelemetryContext
from juturna.telemetry import get_telemetry
from juturna.telemetry.browser import BrowserTelemetry
from juturna.transport import BrowserTransport
from juturna.transport import ThreadingTransport


def _ctx(worker='w1', transport=None):
    return TelemetryContext(transport or BrowserTransport(), worker, '/tmp')


def _record(i):
    return (float(i), 'tx', 'in', 'in', i, i, 10)


def test_batch_is_tagged_and_posted():
    posted = []
    manager = BrowserTelemetry(_ctx('w1'), post=posted.append)

    manager.record_telemetry([_record(0), _record(1)])

    assert len(posted) == 1, f'Expected 1 message, got {len(posted)}'
    assert posted[0]['type'] == 'telemetry', f'Unexpected {posted[0]}'
    assert posted[0]['worker'] == 'w1', f'Unexpected {posted[0]}'
    assert posted[0]['records'][1][-1] == 'w1', f'Got {posted[0]["records"][1]}'
    assert manager.records() == posted[0]['records'], 'Posted != kept'


def test_records_are_limited_like_the_memory_manager():
    manager = BrowserTelemetry(_ctx(), max_records=3, post=lambda m: None)

    manager.record_telemetry([_record(i) for i in range(5)])

    ids = [r[4] for r in manager.records()]
    assert ids == [2, 3, 4], f'Expected the latest 3 records, got {ids}'


def test_empty_batch_is_not_posted():
    posted = []
    manager = BrowserTelemetry(_ctx(), post=posted.append)

    manager.record_telemetry([])

    assert not posted, f'Expected nothing posted, got {posted}'


def test_failing_post_keeps_the_records_and_does_not_raise():
    def post(message):
        raise RuntimeError('no page')

    manager = BrowserTelemetry(_ctx(), post=post)

    manager.record_telemetry([_record(0)])

    assert len(manager.records()) == 1, 'the record must be kept'


def test_registry_builds_it_on_the_browser_transport():
    manager = get_telemetry({'name': 'browser'}, _ctx())

    assert isinstance(manager, BrowserTelemetry), f'Got {type(manager)}'


def test_registry_refuses_it_on_threading():
    ctx = _ctx(transport=ThreadingTransport())

    with pytest.raises(ValueError, match='requires.*page_channel'):
        get_telemetry({'name': 'browser'}, ctx)


def test_failing_post_is_logged_once():
    def post(message):
        raise RuntimeError('no page')

    manager = BrowserTelemetry(_ctx(), post=post)
    manager._logger = mock.Mock()

    for i in range(3):
        manager.record_telemetry([_record(i)])

    assert manager._logger.error.call_count == 1, (
        f'Expected 1 log, got {manager._logger.error.call_count}'
    )
    assert manager.post_failures == 3, f'Got {manager.post_failures}'
    assert len(manager.records()) == 3, 'the records must be kept'


@pytest.mark.parametrize('post', ['postMessage', 5, ['x']])
def test_post_must_be_callable(post):
    with pytest.raises(ValueError, match='post'):
        BrowserTelemetry(_ctx(), post=post)


def test_nothing_is_posted_after_a_stop():
    posted = []
    manager = BrowserTelemetry(_ctx(), post=posted.append)

    manager.stop()
    manager.record_telemetry([_record(0)])

    assert not posted, f'Expected nothing posted, got {posted}'
    assert manager.records() == [], 'Expected no records'
