import logging
import subprocess
import sys
import threading
import time

import numpy as np
import pytest

from juturna.components import Message, Node, State
from juturna.payloads import AudioPayload, ObjectPayload

pytest.importorskip('grpc')

from juturna.cli.commands import _juturna_remote_service as remote  # noqa: E402
from juturna.remotizer.utils import (  # noqa: E402
    create_envelope,
    deserialize_envelope,
    message_to_proto,
)


class Counter(Node):
    """Add 1 to state["count"] and reply with the value it saw."""

    def __init__(self, delay: float = 0.0, **kwargs):
        super().__init__(**kwargs)

        self.delay = delay
        self.gate = threading.Event()
        self.gate.set()
        self.calls = 0

    def update(self, message, state=None):
        self.calls += 1
        self.gate.wait()
        time.sleep(self.delay)

        state['count'] = state.get('count', 0) + 1

        self.transmit(
            Message(
                creator=self.name,
                payload=ObjectPayload(count=state['count']),
            )
        )


class Accumulator(Node):
    """Keep values in state["pending"], reply with their sum every 3."""

    def update(self, message, state=None):
        if message.payload['n'] < 0:
            raise ValueError('negative value')

        if message.payload['n'] == 0:
            state['unsupported'] = {1, 2}

        pending = state.setdefault('pending', list())
        pending.append(message.payload['n'])

        if len(pending) < 3:
            return

        self.transmit(
            Message(creator=self.name, payload=ObjectPayload(sum=sum(pending)))
        )
        pending.clear()


class _Context:
    def __init__(self):
        self.aborted = None

    def abort(self, code, details):
        self.aborted = (code, details)


@pytest.fixture
def service():
    node = Counter(node_name='counter', pipe_name='remote')
    node.start()

    impl = remote.MessagingServiceImpl(node, remote_name='remote')

    yield impl

    impl.shutdown()
    node.kill()


def _envelope(
    pipe_id, sender, state, timeout=30, configuration=None, n=1, stateless=False
):
    return create_envelope(
        message=message_to_proto(
            Message(creator=sender, payload=ObjectPayload(n=n))
        ),
        configuration=configuration or {},
        metadata={},
        creator=sender,
        pipe_id=pipe_id,
        state=state,
        timeout=timeout,
        stateless=stateless,
    )


def _call(service, pipe_id, sender, state, **kwargs):
    context = _Context()
    response = service.SendAndReceive(
        _envelope(pipe_id, sender, state, **kwargs), context
    )

    if context.aborted:
        return context.aborted

    return deserialize_envelope(response)


@pytest.mark.parametrize(
    'first, other',
    [
        (('pipe_x', 'warp'), ('pipe_y', 'warp')),
        (('pipe', 'warp_a'), ('pipe', 'warp_b')),
    ],
    ids=['two_pipelines', 'two_warp_nodes_of_one_pipeline'],
)
def test_overlapping_clients_keep_their_own_state(service, first, other):
    service.node.delay = 0.2
    results = {}

    def send(name, client, count):
        results[name] = _call(service, *client, {'count': count})

    # a1 keeps the node busy and a2 waits in the queue; b arrives meanwhile,
    # which used to re-link the node to b's state before a2 ran
    requests = [('a1', first, 1), ('a2', first, 1), ('b', other, 7)]
    threads = [threading.Thread(target=send, args=r) for r in requests]

    for thread in threads:
        thread.start()
        time.sleep(0.05)

    for thread in threads:
        thread.join()

    assert results['a1']['message'].payload['count'] == 2
    assert results['a2']['message'].payload['count'] == 3
    assert results['a2']['state'] == {'count': 3}
    assert results['b']['message'].payload['count'] == 8
    assert results['b']['state'] == {'count': 8}


def test_client_copy_only_seeds_a_missing_state(service):
    first = _call(service, 'pipe', 'warp', {'count': 1})

    # a stale copy, e.g. sent before the client saw the first response
    second = _call(service, 'pipe', 'warp', {'count': 1})

    assert first['state'] == {'count': 2}
    assert second['state'] == {'count': 3}


def test_the_node_is_never_relinked(service):
    _call(service, 'pipe_x', 'warp', {'count': 1})
    _call(service, 'pipe_y', 'warp', {'count': 7})

    assert service.node._state is None


def test_message_of_a_timed_out_request_is_skipped(service):
    service.node.gate.clear()
    results = []

    def send():
        results.append(_call(service, 'pipe', 'warp', {}, timeout=1))

    senders = [threading.Thread(target=send) for _ in range(2)]

    for sender in senders:
        sender.start()
        time.sleep(0.05)

    for sender in senders:
        sender.join()

    # the first message is already inside update(); the second one is still
    # queued when both requests time out, and must not be processed
    service.node.gate.set()
    time.sleep(0.3)

    assert [r[0].name for r in results] == ['DEADLINE_EXCEEDED'] * 2
    assert service.node.calls == 1
    assert service.get_stats()['timeout_requests'] == 2


def test_stats_keys_are_stable(service):
    keys = set(service.get_stats())

    _call(service, 'pipe', 'warp', {})
    _call(service, '', 'warp', {})

    stats = service.get_stats()

    assert set(stats) == keys
    assert stats['successful_requests'] == 1
    assert stats['invalid_requests'] == 1


def test_missing_pipe_id_or_sender_is_invalid(service):
    for pipe_id, sender in [('', 'warp'), ('pipe', '')]:
        code, _ = _call(service, pipe_id, sender, {})

        assert code.name == 'INVALID_ARGUMENT'


class _Records(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = list()

    def emit(self, record):
        self.messages.append(record.getMessage())


def test_ignored_configuration_is_reported_once_per_client(service):
    records = _Records()
    remote.logger.addHandler(records)

    try:
        for _ in range(3):
            _call(service, 'pipe', 'warp', {}, configuration={'k': 1})

        _call(service, 'pipe', 'other', {}, configuration={'k': 1})
        _call(service, 'pipe', 'plain', {})
    finally:
        remote.logger.removeHandler(records)

    ignored = [m for m in records.messages if 'is ignored' in m]

    assert len(ignored) == 2


@pytest.fixture
def replicas():
    services = list()

    for name in ('a', 'b'):
        node = Accumulator(node_name=f'acc_{name}', pipe_name='remote')
        node.start()
        services.append(remote.MessagingServiceImpl(node, remote_name='r'))

    yield services

    for service in services:
        service.shutdown()
        service.node.kill()


@pytest.mark.parametrize('stateless', [False, True], ids=['sticky', 'stateless'])
def test_update_without_output_is_answered_at_once(replicas, stateless):
    service = replicas[0]
    state = dict()
    responses = list()
    start = time.monotonic()

    for n in (1, 2, 3):
        response = _call(service, 'p', 'w', state, n=n, stateless=stateless)
        state = response['state']
        responses.append(response)

    assert time.monotonic() - start < 1, 'requests waited for their timeout'
    assert [r['message'] for r in responses[:2]] == [None, None]
    assert [r['state'] for r in responses] == [
        {'pending': [1]},
        {'pending': [1, 2]},
        {'pending': []},
    ]
    assert responses[2]['message'].payload['sum'] == 6
    assert all(r['stateless'] == stateless for r in responses)


def test_stateless_clients_can_switch_replica_at_every_request(replicas):
    state = dict()
    sums = list()

    for n in range(1, 7):
        replica = replicas[n % 2]
        response = _call(replica, 'p', 'w', state, n=n, stateless=True)
        state = response['state']

        if response['message'] is not None:
            sums.append(response['message'].payload['sum'])

    assert sums == [6, 15], f'Expected sums [6, 15], got {sums}'
    assert all(replica._state_store == {} for replica in replicas)


def test_sticky_state_stays_on_the_replica(replicas):
    _call(replicas[0], 'p', 'w', {}, n=1)
    response = _call(replicas[1], 'p', 'w', {'pending': [1]}, n=2)

    assert response['state'] == {'pending': [1, 2]}
    assert replicas[0]._state_store[('p', 'w')] == {'pending': [1]}


def test_failing_update_is_answered_at_once(replicas):
    start = time.monotonic()
    code, details = _call(replicas[0], 'p', 'w', {}, n=-1)

    assert time.monotonic() - start < 1, 'request waited for its timeout'
    assert code.name == 'INTERNAL'
    assert 'negative value' in details


def test_stateless_state_with_unsupported_values_fails(replicas):
    code, details = _call(replicas[0], 'p', 'w', {}, n=0, stateless=True)

    assert code.name == 'INTERNAL'
    assert 'a set cannot be sent' in details


def test_stateless_state_keeps_its_types_between_replicas(replicas):
    audio = Message(
        creator='mic',
        version=2,
        payload=AudioPayload(audio=np.arange(4, dtype=np.float32)),
    )
    audio._freeze()
    state = {
        'count': 3,
        'ratio': 1.0,
        'span': (1, 2),
        'raw': b'\x00\xff',
        'context': np.arange(6, dtype=np.int16).reshape(2, 3),
        'gain': np.float32(0.5),
        'by_index': {1: [None, True]},
        'last': audio,
    }

    for replica in replicas:
        state = _call(replica, 'p', 'w', state, n=1, stateless=True)['state']

    assert type(state['count']) is int and state['count'] == 3
    assert type(state['ratio']) is float
    assert state['span'] == (1, 2) and type(state['span']) is tuple
    assert state['raw'] == b'\x00\xff'
    assert state['context'].dtype == np.int16
    assert state['context'].shape == (2, 3)
    assert np.array_equal(state['context'], np.arange(6).reshape(2, 3))
    assert type(state['gain']) is np.float32 and state['gain'] == 0.5
    assert state['by_index'] == {1: [None, True]}
    assert state['pending'] == [1, 1]
    assert np.array_equal(state['last'].payload.audio, audio.payload.audio)
    assert state['last'].version == 2
    assert state['last']._is_frozen


def test_envelope_without_message_is_invalid(service):
    envelope = _envelope('pipe', 'warp', {})
    envelope.ClearField('message')

    context = _Context()
    service.SendAndReceive(envelope, context)

    assert context.aborted[0].name == 'INVALID_ARGUMENT'


def test_idle_states_are_evicted_unless_in_use(service):
    service._seed_state(('p', 'idle'), {'count': 1})
    service._seed_state(('p', 'busy'), {'count': 1})

    with service.requests_lock:
        service.pending_requests[1] = remote.RequestContext(
            'busy', 'e', 1, 30, state_key=('p', 'busy')
        )

    service.STATE_IDLE_TIMEOUT = 0
    time.sleep(0.01)
    service._evict_idle_states()

    assert set(service._state_store) == {('p', 'busy')}


def test_shutdown_stops_the_server_first_then_kills_and_destroys_the_node():
    calls = list()

    class Recorder(Counter):
        def kill(self):
            calls.append('kill')
            super().kill()

        def destroy(self):
            calls.append('destroy')

    class Server:
        def stop(self, grace):
            calls.append(f'server.stop({grace})')

            done = threading.Event()
            done.set()

            return done

    node = Recorder(node_name='counter', pipe_name='remote')
    node.start()
    impl = remote.MessagingServiceImpl(node, remote_name='remote')
    impl._seed_state(('p', 'w'), {'count': 1})

    remote.shutdown(Server(), impl, node)

    assert calls == ['server.stop(5.0)', 'kill', 'destroy']
    assert impl._state_store == {}
    assert node._worker_thread is None


def test_importing_the_service_does_not_configure_root_logging():
    code = (
        'import logging; '
        'import juturna.cli.commands._juturna_remote_service; '
        'print(logging.getLogger().handlers)'
    )
    out = subprocess.run(
        [sys.executable, '-c', code], capture_output=True, text=True
    )

    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == '[]'


def test_remotize_log_level_defaults_to_info():
    import argparse

    from juturna.cli.commands import remotize

    parser = argparse.ArgumentParser()
    remotize.setup_parser(parser.add_subparsers())
    args = parser.parse_args(['remotize', '-n', 'n', '-t', 't'])

    assert args.log_level == 'INFO'


def test_node_without_resolver_uses_the_linked_state():
    node = Counter(node_name='local', pipe_name='p')
    linked = State(count=4)
    node.link_state(linked)

    assert node._resolve_state(Message()) is linked

    node.link_state_resolver(lambda message: Node.SKIP_UPDATE)
    assert node._resolve_state(Message()) is Node.SKIP_UPDATE

    node.link_state_resolver(None)
    assert node._resolve_state(Message()) is linked


def test_skipped_messages_never_reach_update(wait_for_condition):
    node = Counter(node_name='local', pipe_name='p')
    node.link_state(State())
    node.link_state_resolver(
        lambda message: (
            Node.SKIP_UPDATE if message.payload['n'] == 0 else node._state
        )
    )
    node.start()

    try:
        for n in (0, 1, 0, 1):
            node.put(Message(creator='src', payload=ObjectPayload(n=n)))

        assert wait_for_condition(lambda: node._state.get('count') == 2)
        time.sleep(0.1)

        assert node.calls == 2
    finally:
        node.kill()
