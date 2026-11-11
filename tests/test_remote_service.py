import logging
import signal
import subprocess
import sys
import threading
import time

from concurrent import futures

import numpy as np
import pytest

from juturna.components import Message, Node, State
from juturna.payloads import AudioPayload, ObjectPayload

grpc = pytest.importorskip('grpc')

from juturna.cli.commands import _juturna_remote_service as remote  # noqa: E402
from juturna.remotizer.utils import (  # noqa: E402
    PROTOCOL_VERSION,
    create_envelope,
    deserialize_envelope,
    message_to_proto,
    to_typed_value,
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

        if message.payload['n'] == 7:
            for twin in ('first', 'second'):
                self.transmit(
                    Message(creator=self.name, payload=ObjectPayload(t=twin))
                )

            return

        if message.payload['n'] == 8:
            # transmitted once update() returned, e.g. by a thread of the node
            late = Message(creator=self.name, payload=ObjectPayload(t='late'))
            threading.Timer(0.05, self.transmit, args=(late,)).start()

            return

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
        self.callbacks = list()

    def abort(self, code, details):
        self.aborted = (code, details)

    def add_callback(self, callback):
        self.callbacks.append(callback)

        return True


@pytest.fixture
def service():
    node = Counter(node_name='counter', pipe_name='remote')
    node.start()

    impl = remote.MessagingServiceImpl(node, remote_name='remote')

    yield impl

    impl.shutdown()
    node.kill()


SESSION = 'session-of-the-tests'


def _envelope(
    pipe_id,
    sender,
    state,
    timeout=30,
    configuration=None,
    n=1,
    stateless=False,
    session=SESSION,
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
        session=session,
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


@pytest.fixture(params=[False], ids=['lenient'])
def replicas(request):
    services = list()

    for name in ('a', 'b'):
        node = Accumulator(node_name=f'acc_{name}', pipe_name='remote')
        node.start()
        services.append(
            remote.MessagingServiceImpl(
                node, remote_name='r', strict=request.param
            )
        )

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
    assert replicas[0]._state_store[('p', 'w', SESSION)] == {'pending': [1]}


def test_unknown_sticky_client_without_state_is_asked_for_it(replicas):
    code, details = _call(replicas[0], 'p', 'w', None, n=1)

    assert code.name == 'FAILED_PRECONDITION'
    assert 'unknown client w' in details
    assert replicas[0].get_stats()['unknown_client_requests'] == 1
    assert replicas[0]._state_store == {}


def test_known_sticky_client_needs_no_state(replicas):
    _call(replicas[0], 'p', 'w', {}, n=1)
    response = _call(replicas[0], 'p', 'w', None, n=2)

    assert response['state'] == {'pending': [1, 2]}


def test_sticky_client_recovers_its_state_after_a_restart(replicas):
    first, restarted = replicas
    copy = _call(first, 'p', 'w', {}, n=1)['state']
    copy = _call(first, 'p', 'w', None, n=2)['state']

    # the service restarted: it asks for the state, the client sends its copy
    code, _ = _call(restarted, 'p', 'w', None, n=3)
    response = _call(restarted, 'p', 'w', copy, n=3)

    assert code.name == 'FAILED_PRECONDITION'
    assert response['message'].payload['sum'] == 6
    assert response['state'] == {'pending': []}


@pytest.mark.parametrize('stateless', [False, True], ids=['sticky', 'stateless'])
def test_values_that_cannot_be_sent_are_left_out_once_reported(
    replicas, stateless
):
    records = _Records()
    remote.logger.addHandler(records)

    try:
        state = {}

        for _ in range(2):
            state = _call(
                replicas[0], 'p', 'w', state, n=0, stateless=stateless
            )['state']
    finally:
        remote.logger.removeHandler(records)

    assert state == {'pending': [0, 0]}, state
    assert 'unsupported' not in state
    warnings = [m for m in records.messages if 'cannot be sent' in m]
    assert len(warnings) == 1, warnings
    assert "state['unsupported'] (set)" in warnings[0]


def test_only_the_first_message_of_an_update_is_sent(replicas):
    responses = [_call(replicas[0], 'p', 'w', {}, n=7) for _ in range(2)]

    assert [r['message'].payload['t'] for r in responses] == ['first'] * 2


def test_a_message_transmitted_late_is_dropped(replicas, wait_for_condition):
    records = _Records()
    remote.logger.addHandler(records)

    try:
        response = _call(replicas[0], 'p', 'w', {}, n=8)
        reported = wait_for_condition(
            lambda: any(
                'after its update returned' in m for m in records.messages
            ),
            timeout=5.0,
        )
    finally:
        remote.logger.removeHandler(records)

    assert response['message'] is None
    assert reported, f'late message not reported: {records.messages}'
    assert _call(replicas[0], 'p', 'w', None, n=1)['state'] == {
        'pending': [1]
    }


@pytest.mark.parametrize('replicas', [True], ids=['strict'], indirect=True)
@pytest.mark.parametrize('stateless', [False, True], ids=['sticky', 'stateless'])
def test_strict_service_fails_every_request_with_values_it_cannot_send(
    replicas, stateless
):
    for _ in range(2):
        code, details = _call(
            replicas[0], 'p', 'w', {}, n=0, stateless=stateless
        )

        assert code.name == 'DATA_LOSS'
        assert "state['unsupported']: a set cannot be sent" in details

    assert replicas[0].get_stats()['data_loss_requests'] == 2


@pytest.mark.parametrize('replicas', [True], ids=['strict'], indirect=True)
def test_strict_service_fails_an_update_with_two_messages(replicas):
    code, details = _call(replicas[0], 'p', 'w', {}, n=7)

    assert code.name == 'DATA_LOSS'
    assert 'a second message' in details


@pytest.mark.parametrize('replicas', [True], ids=['strict'], indirect=True)
def test_strict_service_fails_the_request_after_a_late_message(
    replicas, wait_for_condition
):
    assert _call(replicas[0], 'p', 'w', {}, n=8)['message'] is None
    assert wait_for_condition(lambda: replicas[0]._late_outputs, timeout=5.0)

    code, details = _call(replicas[0], 'p', 'w', None, n=1)
    after = _call(replicas[0], 'p', 'w', None, n=2)

    assert code.name == 'DATA_LOSS'
    assert 'after its update returned' in details
    assert 'not processed' in details
    assert after['state'] == {'pending': [2]}, 'the failed message was processed'


@pytest.mark.parametrize('replicas', [True], ids=['strict'], indirect=True)
def test_message_transmitted_before_the_response_is_sent_counts_as_late(
    replicas,
):
    service = replicas[0]
    fired = list()

    # a thread of the node transmitting between the end of update() and the
    # response being sent
    def done_then_transmit(message, error):
        service._update_done(message, error)

        if not fired:
            late = Message(creator='acc', payload=ObjectPayload(t='late'))
            late._data_source_id = message.id
            fired.append(late)
            service.put(late)

    service.node.link_update_observer(done_then_transmit)

    first = _call(service, 'p', 'w', {}, n=1)
    code, details = _call(service, 'p', 'w', None, n=2)

    assert first['message'] is None, first
    assert code.name == 'DATA_LOSS', (code, details)
    assert 'after its update returned' in details


def test_stateless_request_without_state_is_invalid(replicas):
    code, _ = _call(replicas[0], 'p', 'w', None, n=1, stateless=True)

    assert code.name == 'INVALID_ARGUMENT'


def test_failing_update_is_answered_at_once(replicas):
    start = time.monotonic()
    code, details = _call(replicas[0], 'p', 'w', {}, n=-1)

    assert time.monotonic() - start < 1, 'request waited for its timeout'
    assert code.name == 'INTERNAL'
    assert 'negative value' in details


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
    service._seed_state(('p', 'idle', SESSION), {'count': 1})
    service._seed_state(('p', 'busy', SESSION), {'count': 1})

    with service.requests_lock:
        service.pending_requests[1] = remote.RequestContext(
            'busy', 'e', 1, 30, state_key=('p', 'busy', SESSION)
        )

    service.STATE_IDLE_TIMEOUT = 0
    time.sleep(0.01)
    service._evict_idle_states()

    assert set(service._state_store) == {('p', 'busy', SESSION)}


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


class Crossing(Node):
    """Answer n=1 from another thread, later; keep n=2 busy; forward n=3."""

    def update(self, message, state=None):
        n = message.payload['n']
        state['seen'] = state.get('seen', 0) + 1

        if n == 1:
            late = Message(
                creator=self.name, payload=ObjectPayload(secret_of='first')
            )
            threading.Timer(0.1, self.transmit, args=(late,)).start()
        elif n == 2:
            time.sleep(0.5)
        elif n == 3:
            self.transmit(message)
        elif n == 4:
            state['big'] = 2**70
        elif n == 5:
            self.transmit(Message(payload=ObjectPayload(n=n)))


@pytest.fixture(params=[False, True], ids=['lenient', 'strict'])
def crossing(request):
    node = Crossing(node_name='crossing', pipe_name='remote')
    node.start()

    impl = remote.MessagingServiceImpl(
        node, remote_name='remote', strict=request.param
    )

    yield impl

    impl.shutdown()
    node.kill()


def test_message_of_another_thread_never_answers_another_client(crossing):
    records = _Records()
    remote.logger.addHandler(records)

    try:
        first = _call(crossing, 'pipe_a', 'warp', {}, n=1)
        # the message made for the first client is transmitted while the
        # message of the second one is inside update()
        second = _call(crossing, 'pipe_b', 'warp', {}, n=2)
    finally:
        remote.logger.removeHandler(records)

    assert first['message'] is None
    assert second['message'] is None, 'output of another client delivered'
    assert second['state'] == {'seen': 1}
    assert any('by another thread' in m for m in records.messages), (
        records.messages
    )

    # the client of that message is not known, so no client pays for it
    assert _call(crossing, 'pipe_b', 'warp', None, n=2)['message'] is None


def test_forwarded_request_message_keeps_the_id_of_its_client(crossing):
    envelope = _envelope('pipe', 'warp', {}, n=3)
    envelope.message.id = 777777

    response = deserialize_envelope(
        crossing.SendAndReceive(envelope, _Context())
    )

    assert response['message'].payload['n'] == 3
    assert response['message'].id == 777777


def test_message_with_the_id_of_a_request_is_not_taken_for_it(service):
    queued = Message(creator='warp', payload=ObjectPayload(n=1))
    queued.id = 5
    other = Message(creator='source', payload=ObjectPayload(n=1))
    other.id = 5

    service.pending_requests[5] = remote.RequestContext(
        sender='warp',
        envelope_id='e',
        message_id=1,
        timeout=30,
        state_key=('pipe', 'warp'),
        state=State(count=2),
        message=queued,
    )

    assert service._resolve_state(other) is Node.SKIP_UPDATE
    assert service._resolve_state(queued) == {'count': 2}


def test_state_value_that_cannot_be_sent_does_not_break_the_client(crossing):
    first = _call(crossing, 'pipe', 'warp', {}, n=4)
    after = _call(crossing, 'pipe', 'warp', None, n=2)

    if crossing.strict:
        for code, details in (first, after):
            assert code.name == 'DATA_LOSS'
            assert "state['big']: a number outside the 64-bit range" in details
    else:
        assert first['state'] == {'seen': 1}
        assert after['state'] == {'seen': 2}

    assert crossing.get_stats()['invalid_requests'] == 0


def test_response_that_cannot_be_sent_is_not_an_invalid_request(crossing):
    code, details = _call(crossing, 'pipe', 'warp', {}, n=5)

    assert code.name == ('DATA_LOSS' if crossing.strict else 'INTERNAL')
    assert 'message.creator: None cannot be sent' in details
    assert crossing.get_stats()['invalid_requests'] == 0


def test_new_sticky_clients_are_refused_beyond_the_limit():
    node = Counter(node_name='counter', pipe_name='remote')
    node.start()
    service = remote.MessagingServiceImpl(node, remote_name='r', max_clients=1)

    try:
        known = _call(service, 'pipe_a', 'warp', {})
        code, details = _call(service, 'pipe_b', 'warp', {})
        stateless = _call(service, 'pipe_c', 'warp', {}, stateless=True)

        assert known['state'] == {'count': 1}
        assert code.name == 'RESOURCE_EXHAUSTED'
        assert 'state of 1 clients' in details
        assert stateless['state'] == {'count': 1}, 'stateless clients refused'
        assert _call(service, 'pipe_a', 'warp', None)['state'] == {'count': 2}
        assert service.get_stats()['refused_requests'] == 1
    finally:
        service.shutdown()
        node.kill()


def test_message_of_a_client_that_left_is_skipped(service, wait_for_condition):
    service.node.gate.clear()
    contexts = [_Context(), _Context()]
    results = dict()

    def send(index):
        response = service.SendAndReceive(
            _envelope('pipe', f'warp_{index}', {}), contexts[index]
        )
        results[index] = contexts[index].aborted or response

    senders = [threading.Thread(target=send, args=(i,)) for i in range(2)]

    for sender in senders:
        sender.start()
        assert wait_for_condition(
            lambda: len(service.pending_requests) == senders.index(sender) + 1,
            interval=0.01,
        )

    # the first message is inside update(), the second one is still queued
    # when its client cancels the call
    for callback in contexts[1].callbacks:
        callback()

    senders[1].join(timeout=5.0)
    service.node.gate.set()
    senders[0].join(timeout=5.0)

    assert results[1][0].name == 'DEADLINE_EXCEEDED'
    assert 'Client gone' in results[1][1]
    assert deserialize_envelope(results[0])['state'] == {'count': 1}
    assert wait_for_condition(lambda: service.node._queue.empty())
    assert service.node.calls == 1


@pytest.mark.parametrize('state', [3, [1, 2]], ids=['int', 'list'])
def test_state_that_is_not_a_dict_is_invalid(service, state):
    envelope = _envelope('pipe', 'warp', {})
    envelope.state.CopyFrom(to_typed_value(state))

    context = _Context()
    service.SendAndReceive(envelope, context)

    assert context.aborted[0].name == 'INVALID_ARGUMENT'
    assert service.node.calls == 0


def _remotize_args(tmp_path, monkeypatch, *arguments):
    import argparse

    from juturna.cli.commands import remotize

    # the service creates its runtime folder in the working directory
    monkeypatch.chdir(tmp_path)

    parser = argparse.ArgumentParser()
    remotize.setup_parser(parser.add_subparsers())

    return parser.parse_args(['remotize', '-n', 'node', *arguments])


def test_serve_fails_when_the_node_cannot_be_built(tmp_path, monkeypatch):
    args = _remotize_args(
        tmp_path, monkeypatch, '-t', 'contrib.jt_test.nodes.Missing'
    )

    assert remote.serve(args) == 1


def test_serve_fails_when_the_port_is_taken(tmp_path, monkeypatch):
    import socket

    taken = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    taken.bind(('127.0.0.1', 0))
    taken.listen()
    destroyed = list()

    from juturna.contrib.jt_test.nodes import PassthroughIdentity

    monkeypatch.setattr(
        PassthroughIdentity, 'destroy', lambda self: destroyed.append(self)
    )

    try:
        args = _remotize_args(
            tmp_path,
            monkeypatch,
            '-t',
            'contrib.jt_test.nodes.PassthroughIdentity',
            '-p',
            str(taken.getsockname()[1]),
        )

        assert remote.serve(args) == 1
    finally:
        taken.close()

    assert len(destroyed) == 1, 'the node built for the service was kept'
    assert destroyed[0]._worker_thread is None


def test_remotize_command_exits_with_the_code_of_the_service(tmp_path):
    import os

    out = subprocess.run(
        [sys.executable, '-m', 'juturna', 'remotize', '-n', 'node']
        + ['-t', 'contrib.jt_test.nodes.Missing'],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path)},
    )

    assert out.returncode == 1, out.stderr


def test_response_carries_the_protocol_version_and_the_session(service):
    response = _call(service, 'pipe', 'warp', {})

    assert response['protocol_version'] == PROTOCOL_VERSION
    assert response['session'] == SESSION


@pytest.mark.parametrize('version', [0, PROTOCOL_VERSION + 1])
@pytest.mark.parametrize('method', ['SendAndReceive', 'EndSession'])
def test_another_protocol_version_is_refused(service, method, version):
    envelope = _envelope('pipe', 'warp', {})
    envelope.protocol_version = version
    context = _Context()

    getattr(service, method)(envelope, context)

    code, details = context.aborted

    assert code.name == 'UNIMPLEMENTED'
    assert f'version {version} ' in details
    assert service.node.calls == 0
    assert service._state_store == {}


@pytest.mark.parametrize('method', ['SendAndReceive', 'EndSession'])
def test_request_without_a_session_is_invalid(service, method):
    context = _Context()

    getattr(service, method)(
        _envelope('pipe', 'warp', {}, session=''), context
    )

    code, details = context.aborted

    assert code.name == 'INVALID_ARGUMENT'
    assert 'session' in details
    assert service.node.calls == 0


def test_another_session_cannot_reach_the_state_of_a_client(service):
    assert _call(service, 'pipe', 'warp', {'count': 5})['state'] == {'count': 6}

    # the same names, without the session of the client: no state to read
    code, _ = _call(service, 'pipe', 'warp', None, session='guess')

    assert code.name == 'FAILED_PRECONDITION'

    # nor to change: it gets a state of its own
    other = _call(service, 'pipe', 'warp', {'count': 100}, session='guess')

    assert other['state'] == {'count': 101}
    assert _call(service, 'pipe', 'warp', None)['state'] == {'count': 7}


def test_pipeline_started_again_does_not_continue_from_the_old_state(service):
    _call(service, 'pipe', 'warp', {'count': 5}, session='first run')

    # the new run sends its own state when asked, as any unknown client
    code, _ = _call(service, 'pipe', 'warp', None, session='second run')

    assert code.name == 'FAILED_PRECONDITION'
    assert _call(service, 'pipe', 'warp', {}, session='second run')[
        'state'
    ] == {'count': 1}


def test_ending_a_session_drops_its_state_only(service):
    _call(service, 'pipe', 'warp', {'count': 5})
    _call(service, 'pipe', 'warp', {'count': 50}, session='other')

    for session in ('guess', SESSION, SESSION):
        context = _Context()
        ended = service.EndSession(
            _envelope('pipe', 'warp', None, session=session), context
        )

        assert context.aborted is None
        assert ended.protocol_version == PROTOCOL_VERSION

    assert set(service._state_store) == {('pipe', 'warp', 'other')}
    assert set(service._state_last_used) == {('pipe', 'warp', 'other')}

    code, _ = _call(service, 'pipe', 'warp', None)

    assert code.name == 'FAILED_PRECONDITION'


def test_sessions_are_not_logged(service):
    records = list()
    handler = logging.Handler()
    handler.emit = lambda record: records.append(record.getMessage())
    level = remote.logger.level
    remote.logger.addHandler(handler)
    remote.logger.setLevel(logging.DEBUG)
    service.STATE_IDLE_TIMEOUT = 0

    try:
        _call(service, 'pipe', 'warp', {}, configuration={'k': 1})
        _call(service, 'pipe', 'gone', {})
        _call(service, 'pipe', 'warp', None, session='unknown session')
        time.sleep(0.01)
        service._evict_idle_states()
        service.EndSession(_envelope('pipe', 'warp', None), _Context())
    finally:
        remote.logger.removeHandler(handler)
        remote.logger.setLevel(level)

    assert any('created state' in record for record in records)
    assert any('dropped idle state' in record for record in records)
    assert not any('session' in record.replace('session of', '') for record in records)
    assert not any(SESSION in record for record in records)


def test_message_of_an_unknown_payload_type_is_an_invalid_request(service):
    envelope = _envelope('pipe', 'warp', {})
    envelope.message.payload.Pack(to_typed_value({'a': 1}))
    context = _Context()

    service.SendAndReceive(envelope, context)

    code, details = context.aborted

    assert code.name == 'INVALID_ARGUMENT'
    assert 'unknown payload type' in details
    assert service.node.calls == 0


@pytest.mark.parametrize(
    'host, address, loopback',
    [
        ('127.0.0.1', '127.0.0.1:7', True),
        ('localhost', 'localhost:7', True),
        ('::1', '[::1]:7', True),
        ('[::1]', '[::1]:7', True),
        ('0.0.0.0', '0.0.0.0:7', False),
        ('::', '[::]:7', False),
        ('192.0.2.1', '192.0.2.1:7', False),
        ('node.example', 'node.example:7', False),
    ],
)
def test_listen_address_and_loopback(host, address, loopback):
    assert remote._listen_address(host, 7) == address
    assert remote._is_loopback(host) is loopback


@pytest.mark.parametrize(
    'arguments, address, warned',
    [
        ((), '127.0.0.1:50051', False),
        (('--host', '0.0.0.0', '-p', '7'), '0.0.0.0:7', True),
        (('-H', '::1', '-p', '7'), '[::1]:7', False),
    ],
    ids=['default', 'all_addresses', 'ipv6_loopback'],
)
def test_serve_listens_on_loopback_unless_told_otherwise(
    tmp_path, monkeypatch, arguments, address, warned
):
    listened = list()
    warnings = list()

    class Server:
        def add_insecure_port(self, target):
            listened.append(target)

            return 1

        def start(self):
            # stop right after the start, as a signal would
            signal.raise_signal(signal.SIGTERM)

        def stop(self, grace):
            stopped = threading.Event()
            stopped.set()

            return stopped

    monkeypatch.setattr(remote.grpc, 'server', lambda *a, **k: Server())
    monkeypatch.setattr(
        remote.messaging_service_pb2_grpc,
        'add_MessagingServiceServicer_to_server',
        lambda *a: None,
    )
    monkeypatch.setattr(
        remote.logger, 'warning', lambda text: warnings.append(text)
    )
    previous = {
        signum: signal.getsignal(signum)
        for signum in (signal.SIGINT, signal.SIGTERM)
    }

    try:
        args = _remotize_args(
            tmp_path,
            monkeypatch,
            '-t',
            'contrib.jt_test.nodes.PassthroughIdentity',
            *arguments,
        )

        assert remote.serve(args) == 0
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)

    assert listened == [address]
    assert any('trusted networks only' in w for w in warnings) is warned


@pytest.fixture
def channel(service):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    remote.messaging_service_pb2_grpc.add_MessagingServiceServicer_to_server(
        service, server
    )
    port = server.add_insecure_port('127.0.0.1:0')
    server.start()

    with grpc.insecure_channel(f'127.0.0.1:{port}') as open_channel:
        yield remote.messaging_service_pb2_grpc.MessagingServiceStub(
            open_channel
        )

    server.stop(None).wait(5)


def test_session_lifecycle_through_a_real_channel(channel):
    first = deserialize_envelope(
        channel.SendAndReceive(_envelope('pipe', 'warp', {'count': 5}))
    )

    assert first['state'] == {'count': 6}
    assert first['message'].payload['count'] == 6

    with pytest.raises(grpc.RpcError) as error:
        channel.SendAndReceive(_envelope('pipe', 'warp', None, session='guess'))

    assert error.value.code() == grpc.StatusCode.FAILED_PRECONDITION

    channel.EndSession(_envelope('pipe', 'warp', None))

    with pytest.raises(grpc.RpcError) as error:
        channel.SendAndReceive(_envelope('pipe', 'warp', None))

    assert error.value.code() == grpc.StatusCode.FAILED_PRECONDITION


def test_protocol_mismatch_through_a_real_channel(channel):
    envelope = _envelope('pipe', 'warp', {})
    envelope.protocol_version = 0

    with pytest.raises(grpc.RpcError) as error:
        channel.SendAndReceive(envelope)

    assert error.value.code() == grpc.StatusCode.UNIMPLEMENTED
    assert 'version 0' in error.value.details()
