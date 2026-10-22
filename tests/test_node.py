import time
import threading

import pytest

import juturna as jt

def test_data_source_id_properly_set(test_config, wait_for_condition):
    p = test_config['test_pipeline_folder']

    pipeline_config = {
        'version': '0.2.0',
        "pipeline": {
            'name': 'e2e_test_pipeline_generated_messages',
            'id': 'e2e_1',
            'folder': f'{p}/e2e_test_pipeline',
            'nodes': [
                {
                    'name': 'source_1',
                    'type': 'contrib.jt_test.nodes.Sequencer',
                    'configuration': {}
                },
                {
                    'name': 'sink_1',
                    'type': 'contrib.jt_test.nodes.Crasher',
                    'configuration': {}
                }
            ],
            'links': [{'from': 'source_1', 'to': 'sink_1'}]
        }
    }

    pipeline = jt.components.Pipeline(pipeline_config)
    pipeline.warmup()

    pipeline.start()
    assert wait_for_condition(lambda: len(pipeline._nodes['sink_1'].messages) >= 4, timeout=5), (
        "Expected at least 4 messages to be transmitted within 5 seconds")
    pipeline.stop()

    out_messages = pipeline._nodes['sink_1'].messages

    assert len(out_messages) == 4, f"Expected 4 messages, got {len(out_messages)}"

    assert out_messages[0]._data_source_id == 0, f"Expected data source ID 0, got {out_messages[0]._data_source_id}"


def test_pipeline_draining_on_stop(test_config, wait_for_condition):
    """
    Verify that when the pipeline is stopped, all messages that were sent by the source before the stop
    are actually received by the sink, despite internal delays.
    """
    p = test_config['test_pipeline_folder']

    pipeline_config = {
        "version": "0.1.0",
        "pipeline": {
            "name": "e2e_test_draining_pipeline",
            "id": "e2e_2",
            "folder": f'{p}/e2e_test_draining_pipeline',
            "nodes": [
                {
                    "name": "0_stream",
                    "type": "contrib.jt_test.nodes.DataStreamer",
                    "configuration": { "rate": 2 }
                },
                {
                    "name": "1_pass",
                    "type": "contrib.jt_test.nodes.PassthroughIdentity",
                    "configuration": { "delay": 2 }
                },
                {
                    'name': '2_sink',
                    'type': 'contrib.jt_test.nodes.Crasher',
                    'configuration': {}
                }
            ],
            "links": [
                {"from": "0_stream", "to": "1_pass"},
                {"from": "1_pass", "to": "2_sink"}
            ]
        }
    }

    pipeline = jt.components.Pipeline(pipeline_config)
    pipeline.warmup()
    pipeline.start()

    wait_for_condition(lambda: pipeline._node_state_store['0_stream'].get('transmitted', 0) > 10, timeout=5)
    sent_count = pipeline._node_state_store['0_stream']['transmitted']
    pipeline.stop()

    received_messages = pipeline._nodes['2_sink'].messages
    received_count = len(received_messages)

    assert received_count == sent_count, (
        f"Draining failed: sent {sent_count}, but only received {received_count}. "
    )

def test_pipeline_immediate_stop(test_config, wait_for_condition):
    p = test_config['test_pipeline_folder']

    pipeline_config = {
        "version": "0.1.0",
        "pipeline": {
            "name": "e2e_test_draining_pipeline",
            "id": "e2e_2",
            "folder": f'{p}/e2e_test_draining_pipeline',
            "nodes": [
                {
                    "name": "0_stream",
                    "type": "contrib.jt_test.nodes.DataStreamer",
                    "configuration": { "rate": 2 }
                },
                {
                    "name": "1_pass",
                    "type": "contrib.jt_test.nodes.PassthroughIdentity",
                    "configuration": { "delay": 2 }
                },
                {
                    'name': '2_sink',
                    'type': 'contrib.jt_test.nodes.Crasher',
                    'configuration': {}
                }
            ],
            "links": [
                {"from": "0_stream", "to": "1_pass"},
                {"from": "1_pass", "to": "2_sink"}
            ]
        }
    }

    pipeline = jt.components.Pipeline(pipeline_config)
    pipeline.warmup()
    pipeline.start()

    wait_for_condition(lambda: pipeline._node_state_store['0_stream'].get('transmitted', 0) > 10, timeout=5)
    sent_count = pipeline._node_state_store['0_stream']['transmitted']

    received_messages = pipeline._nodes['2_sink'].messages
    received_count = len(received_messages)

    for node in pipeline._nodes.values():
        node.kill()

    received_messages = pipeline._nodes['2_sink'].messages
    received_count = len(received_messages)

    assert received_count < sent_count, (
        f"Immediate stop failed: the pipe waits for all the {sent_count} messages to be processed before stopping."
    )


def test_pipeline_kill_discards_pending_messages(test_config, wait_for_condition):
    """
    Verify that killing a pipeline does not process the messages still pending
    in the nodes: the slow node has a backlog when the kill is issued, and none
    of the backlog reaches the sink.
    """
    p = test_config['test_pipeline_folder']
    delay = 1

    pipeline_config = {
        "version": "0.1.0",
        "pipeline": {
            "name": "e2e_test_kill_pipeline",
            "id": "e2e_3",
            "folder": f'{p}/e2e_test_kill_pipeline',
            "nodes": [
                {
                    "name": "0_stream",
                    "type": "contrib.jt_test.nodes.DataStreamer",
                    "configuration": { "rate": 10 }
                },
                {
                    "name": "1_pass",
                    "type": "contrib.jt_test.nodes.PassthroughIdentity",
                    "configuration": { "delay": delay }
                },
                {
                    'name': '2_sink',
                    'type': 'contrib.jt_test.nodes.Crasher',
                    'configuration': {}
                }
            ],
            "links": [
                {"from": "0_stream", "to": "1_pass"},
                {"from": "1_pass", "to": "2_sink"}
            ]
        }
    }

    pipeline = jt.components.Pipeline(pipeline_config)
    pipeline.warmup()
    pipeline.start()

    # the source produces 10 msg/s, the proc node consumes 1 msg/s: wait until
    # a backlog has accumulated in the proc node
    assert wait_for_condition(
        lambda: pipeline._node_state_store['0_stream'].get('transmitted', 0) >= 15,
        timeout=5,
    ), "source did not produce enough messages"

    sink = pipeline._nodes['2_sink']
    received_before_kill = len(sink.messages)

    t0 = time.monotonic()
    pipeline.kill()
    elapsed = time.monotonic() - t0

    sent_count = pipeline._node_state_store['0_stream']['transmitted']
    received_count = len(sink.messages)

    # at most the update in progress in the proc node, plus one message already
    # in flight towards the sink, can be delivered after the kill
    assert received_count <= received_before_kill + 2, (
        f"pending messages processed after kill: {received_before_kill} "
        f"received before, {received_count} after"
    )
    assert sent_count - received_count >= 10, (
        f"expected a discarded backlog, sent {sent_count}, received {received_count}"
    )

    # draining the backlog would take ~delay seconds per message
    assert elapsed < 2 * delay + 1, f"kill took {elapsed:.2f}s, pipe was drained"

    for node in pipeline._nodes.values():
        assert node._queue.empty(), f"{node.name} input queue not cleared"


def test_node_survives_exception_in_update(wait_for_condition):
    class Boom(jt.components.Node):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

            self.calls = 0

        def update(self, message, **kwargs):
            self.calls += 1

            raise RuntimeError('boom')

    node = Boom(node_name='b', pipe_name='p')
    node.start()

    for _ in range(5):
        node.put(jt.components.Message())
        time.sleep(0.1)

    assert wait_for_condition(lambda: node.calls == 5, timeout=5), 'node died'
    assert node._worker_thread.is_alive()
    assert node._update_failures == 5

    assert node.health['source_failures'] == 0
    assert node.health['worker_failures'] == 0
    assert node.health['update_failures'] == 5
    assert node.health['last_failure_at'] != None

    node.stop()


def test_node_survives_exception_in_source(wait_for_condition):
    class Boom(jt.components.Node):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

            self.calls = 0

    node = Boom(node_name='test', pipe_name='p')

    def faulty_source():
        raise RuntimeError('this is failing!')

    node.set_source(faulty_source, by=0.2)
    node.start()

    assert wait_for_condition(lambda: node._source_failures >= 2)
    assert node._source_thread.is_alive()
    node.stop()


@pytest.mark.parametrize('mode', ['post', 'pre'])
def test_source_returning_none_does_not_spin(mode):
    calls = 0

    def idle_source():
        nonlocal calls
        calls += 1

        return None

    node = jt.components.Node(node_name='idle', pipe_name='p')
    node.set_source(idle_source, by=0.1, mode=mode)
    node.start()

    time.sleep(0.5)
    node.stop()

    # about 5 calls are expected in 0.5 s, before the fix there were millions
    assert 2 <= calls <= 8, f'{calls} calls in 0.5 s with by=0.1'


@pytest.mark.parametrize('mode', ['post', 'pre'])
def test_failing_source_backs_off(mode):
    node = jt.components.Node(node_name='failing', pipe_name='p')

    def faulty_source():
        raise RuntimeError('this is failing!')

    # by=0 used to retry a failing source in a tight loop
    node.set_source(faulty_source, by=0, mode=mode)
    node.start()

    time.sleep(1.0)
    node.stop()

    # backoff waits 0.1, 0.2, 0.4, 0.8 s: at most 4 or 5 calls in 1 s
    assert 2 <= node.health['source_failures'] <= 6


def test_source_backoff_doubles_up_to_cap(monkeypatch):
    monkeypatch.setattr(jt.meta, 'JUTURNA_SOURCE_MAX_BACKOFF', 1.0)

    node = jt.components.Node(node_name='backoff', pipe_name='p')

    node.set_source(lambda: None, by=0)
    delays = [node._source_backoff(n) for n in range(1, 7)]

    assert delays == [0.1, 0.2, 0.4, 0.8, 1.0, 1.0]

    # a cap below the source interval never shortens the interval itself
    node.set_source(lambda: None, by=2.0)

    assert node._source_backoff(1) == 2.0
    assert node._source_backoff(3) == 2.0


def test_stop_interrupts_source_backoff():
    node = jt.components.Node(node_name='slow_backoff', pipe_name='p')

    def faulty_source():
        raise RuntimeError('this is failing!')

    node.set_source(faulty_source, by=10)
    node.start()

    time.sleep(0.2)

    start = time.monotonic()
    node.stop()

    assert node.health['source_failures'] == 1
    assert time.monotonic() - start < 1.0, 'stop() waited for the backoff'


class _Joiner(jt.components.Node):
    """Pair one message from each of two creators, waiting in the state"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.received = list()
        self.pairs = list()

    def update(self, message, **kwargs):
        self.received.append(message)

        pending = kwargs['state'].setdefault('pending', {'a': [], 'b': []})
        pending[message.creator].append(message)

        if pending['a'] and pending['b']:
            self.pairs.append(
                (pending['a'].pop(0).version, pending['b'].pop(0).version)
            )


def test_messages_from_several_creators_arrive_one_at_a_time(
    wait_for_condition,
):
    node = _Joiner(node_name='joiner', pipe_name='p')
    state = jt.components.State()
    node.link_state(state)
    node.start()

    try:
        for version in range(3):
            node.put(jt.components.Message(creator='a', version=version))

        for version in range(2):
            node.put(jt.components.Message(creator='b', version=version))

        assert wait_for_condition(lambda: len(node.received) == 5, timeout=5)
    finally:
        node.stop()

    assert all(
        isinstance(m.payload, jt.payloads.Batch) is False
        for m in node.received
    ), 'messages must not be wrapped in a batch'
    assert [m.creator for m in node.received] == ['a', 'a', 'a', 'b', 'b']
    assert node.pairs == [(0, 0), (1, 1)]
    assert [m.version for m in state['pending']['a']] == [2], (
        'the unmatched message must wait in the state'
    )
    assert state['pending']['b'] == []


def test_state_survives_a_restart(wait_for_condition):
    node = _Joiner(node_name='restarted', pipe_name='p')
    state = jt.components.State()
    node.link_state(state)

    node.start()
    node.put(jt.components.Message(creator='a', version=0))
    assert wait_for_condition(lambda: len(node.received) == 1, timeout=5)
    node.stop()

    node.start()
    node.put(jt.components.Message(creator='b', version=0))
    assert wait_for_condition(lambda: len(node.received) == 2, timeout=5)
    node.stop()

    assert node.pairs == [(0, 0)]


def test_node_runs_a_single_worker_thread():
    node = jt.components.Node(node_name='single', pipe_name='p')
    node.start()

    try:
        names = {t.name for t in threading.enumerate()}

        assert '_worker_single' in names
        assert not any(n.endswith('_single') and n != '_worker_single'
                       for n in names), names
    finally:
        node.stop()
