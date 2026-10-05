import pytest

from juturna.components import Pipeline
from juturna.transport import ThreadingTransport


class Collector:
    """Stands for a node of another worker: all it needs is put()."""

    def __init__(self):
        self.messages = list()

    def put(self, message):
        self.messages.append(message)


class RemoteTransport(ThreadingTransport):
    def __init__(self):
        super().__init__()

        self.destinations = dict()

    def remote_destination(self, node_name):
        return self.destinations.setdefault(node_name, Collector())


def _config(tmp_path, sink_worker='b'):
    return {
        'plugins': ['tests/test_plugins'],
        'pipeline': {
            'name': 'workers',
            'id': 'workers-1',
            'folder': str(tmp_path),
            'nodes': [
                {
                    'name': 's',
                    'type': 'source',
                    'mark': 'data_streamer',
                    'configuration': {'rate': 20},
                },
                {
                    'name': 'k',
                    'type': 'sink',
                    'mark': 'dumper',
                    'configuration': {},
                    'worker': sink_worker,
                },
            ],
            'links': [{'from': 's', 'to': 'k'}],
        },
    }


def test_only_the_nodes_of_the_worker_are_built(tmp_path):
    main = Pipeline(_config(tmp_path))
    main._transport = RemoteTransport()
    main.warmup()

    other = Pipeline(_config(tmp_path), worker='b')
    other.warmup()

    assert list(main._nodes) == ['s'], f'main built {list(main._nodes)}'
    assert list(other._nodes) == ['k'], f'b built {list(other._nodes)}'


def test_link_from_another_worker_adds_an_origin(tmp_path):
    other = Pipeline(_config(tmp_path), worker='b')
    other.warmup()

    origins = other._nodes['k'].origins
    assert origins == ['s'], f'Expected origins [s], got {origins}'


def test_link_to_another_worker_goes_through_the_transport(
    tmp_path, wait_for_condition
):
    transport = RemoteTransport()
    main = Pipeline(_config(tmp_path))
    main._transport = transport

    main.warmup()
    main.start()

    remote = transport.destinations['k']
    arrived = wait_for_condition(lambda: len(remote.messages) >= 2, timeout=5)
    main.stop()

    assert arrived, f'Expected 2 messages, got {len(remote.messages)}'


def test_link_to_another_worker_needs_transport_support(tmp_path):
    main = Pipeline(_config(tmp_path))

    with pytest.raises(ValueError, match='node k runs in another worker'):
        main.warmup()


def test_nodes_default_to_the_main_worker(tmp_path):
    config = _config(tmp_path, sink_worker='main')
    del config['pipeline']['nodes'][1]['worker']

    main = Pipeline(config)
    main.warmup()

    assert sorted(main._nodes) == ['k', 's'], f'built {sorted(main._nodes)}'
