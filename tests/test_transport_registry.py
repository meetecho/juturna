import pytest

from juturna.components import Pipeline
from juturna.transport import BrowserTransport
from juturna.transport import ThreadingTransport
from juturna.transport import get_transport


def test_default_transport_is_threading():
    transport = get_transport()

    assert isinstance(transport, ThreadingTransport), (
        f'Expected ThreadingTransport, got {type(transport).__name__}'
    )


def test_transport_by_name():
    assert isinstance(get_transport('browser'), BrowserTransport)
    assert isinstance(get_transport({'name': 'threading'}), ThreadingTransport)


def test_transport_options_reach_the_backend():
    transport = get_transport(
        {'name': 'browser', 'max_payload_bytes': 4_000_000, 'queue_capacity': 4}
    )

    assert transport._max_payload_bytes == 4_000_000, (
        f'Got {transport._max_payload_bytes}'
    )
    assert transport._queue_capacity == 4, f'Got {transport._queue_capacity}'


def test_unknown_transport_is_rejected():
    with pytest.raises(ValueError, match='unknown transport backend'):
        get_transport('carrier-pigeon')

    with pytest.raises(ValueError, match='unknown transport backend'):
        get_transport({'name': 'carrier-pigeon'})


def test_unknown_option_is_rejected():
    with pytest.raises(ValueError, match="invalid options for the 'browser'"):
        get_transport({'name': 'browser', 'max_payload': 1})

    with pytest.raises(ValueError, match="invalid options for the 'threading'"):
        get_transport({'name': 'threading', 'max_payload_bytes': 1})


def test_pipeline_configures_its_transport(tmp_path):
    config = {
        'pipeline': {
            'name': 'configured',
            'id': 'configured-1',
            'folder': str(tmp_path),
            'transport': {'name': 'browser', 'max_payload_bytes': 4_000_000},
            'nodes': [],
            'links': [],
        }
    }

    transport = Pipeline(config)._transport

    assert transport._max_payload_bytes == 4_000_000, (
        f'Got {transport._max_payload_bytes}'
    )
