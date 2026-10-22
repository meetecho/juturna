import logging
import subprocess
import sys
import threading
import time

import pytest

from juturna.components import Message, Node, State
from juturna.payloads import Batch, ObjectPayload

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


def _envelope(pipe_id, sender, state, timeout=30, configuration=None):
    return create_envelope(
        message=message_to_proto(
            Message(creator=sender, payload=ObjectPayload(n=1))
        ),
        configuration=configuration or {},
        metadata={},
        creator=sender,
        pipe_id=pipe_id,
        state=state,
        timeout=timeout,
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


def test_batch_with_messages_of_two_clients_is_rejected(service):
    service._seed_state(('p', 'a'), {})
    service._seed_state(('p', 'b'), {})

    with service.requests_lock:
        service.pending_requests[101] = remote.RequestContext(
            'a', 'e1', 1, 30, state_key=('p', 'a')
        )
        service.pending_requests[102] = remote.RequestContext(
            'b', 'e2', 2, 30, state_key=('p', 'b')
        )

    inner = [Message(creator='x', payload=ObjectPayload()) for _ in range(2)]
    inner[0].id, inner[1].id = 101, 102

    with pytest.raises(ValueError, match='mixes messages'):
        service._resolve_state(Message(payload=Batch(messages=tuple(inner))))

    inner[1].id = 101
    state = service._resolve_state(Message(payload=Batch(messages=tuple(inner))))

    assert state is service._state_store[('p', 'a')]


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
    assert node._worker_thread is None and node._update_thread is None


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
