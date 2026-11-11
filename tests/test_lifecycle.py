"""
What happens when the cleanup of a node fails, when a stop does not come
back, and when something that is not a message enters a node.
"""

import logging
import threading
import time

import pytest

import juturna as jt

from juturna.components import Message
from juturna.components import Node
from juturna.components import PipelineBusyError
from juturna.components import PipelineDestroyedError
from juturna.components import PipelineNotReadyError


class _CleanupError(Exception):
    pass


class _Collector(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.seen = list()

    def update(self, message: Message, **kwargs):
        self.seen.append(message.version)


class _Blocker(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.busy = threading.Event()
        self.release = threading.Event()
        self.calls = 0

    def update(self, message: Message, **kwargs):
        self.calls += 1
        self.busy.set()
        self.release.wait()


def _config(name: str, folder: str) -> dict:
    return {
        'version': '0.2.0',
        'pipeline': {
            'name': name,
            'id': name,
            'folder': f'{folder}/{name}',
            'nodes': [
                {
                    'name': 'source_1',
                    'type': 'contrib.jt_test.nodes.Sequencer',
                    'configuration': {},
                },
                {
                    'name': 'mid_1',
                    'type': 'contrib.jt_test.nodes.PassthroughIdentity',
                    'configuration': {},
                },
                {
                    'name': 'sink_1',
                    'type': 'contrib.jt_test.nodes.Crasher',
                    'configuration': {},
                },
            ],
            'links': [
                {'from': 'source_1', 'to': 'mid_1'},
                {'from': 'mid_1', 'to': 'sink_1'},
            ],
        },
    }


def _running_pipeline(name: str, test_config, wait_for_condition):
    pipeline = jt.components.Pipeline(
        _config(name, test_config['test_pipeline_folder'])
    )

    pipeline.warmup()
    pipeline.start()

    assert wait_for_condition(
        lambda: len(pipeline._nodes['sink_1'].messages) > 0
    ), 'expected sink_1 to receive at least one message'

    return pipeline


def _alive_workers(node_names) -> list[str]:
    names = {
        f'_{kind}_{node_name}'
        for kind in ('worker', 'source')
        for node_name in node_names
    }

    return sorted(t.name for t in threading.enumerate() if t.name in names)


def _raising(error=_CleanupError):
    def method():
        raise error('cleanup failed')

    return method


def _block_node(pipeline, node_name: str, monkeypatch):
    """Make update() of a node wait until the returned event is set"""
    node = pipeline._nodes[node_name]
    busy = threading.Event()
    release = threading.Event()

    def update(message, **kwargs):
        busy.set()
        release.wait()

    monkeypatch.setattr(node, 'update', update)

    assert busy.wait(timeout=5), f'{node_name} did not receive a message'

    return release


# -- a node whose cleanup raises ---------------------------------------------


@pytest.mark.parametrize('operation', ['stop', 'kill'])
def test_a_raising_node_stop_still_stops_every_node(
    test_config, wait_for_condition, monkeypatch, operation
):
    pipeline = _running_pipeline(
        f'raising_stop_{operation}', test_config, wait_for_condition
    )
    node_names = list(pipeline._nodes)

    # the node cleanup fails before it reaches Node.stop()
    monkeypatch.setattr(pipeline._nodes['mid_1'], 'stop', _raising())

    with pytest.raises(_CleanupError):
        getattr(pipeline, operation)()

    assert pipeline.status['self'] == 'pipeline_stopped'
    assert _alive_workers(node_names) == []
    assert all(
        node['status'] == 'component_stopped'
        for node in pipeline.status['nodes'].values()
    )

    pipeline.destroy()

    assert pipeline.status['self'] == 'pipeline_destroyed'


def test_a_raising_node_destroy_still_destroys_every_node(
    test_config, wait_for_condition, monkeypatch
):
    pipeline = _running_pipeline(
        'raising_destroy', test_config, wait_for_condition
    )
    node_names = list(pipeline._nodes)
    destroyed = list()

    for node_name in ('source_1', 'sink_1'):
        monkeypatch.setattr(
            pipeline._nodes[node_name],
            'destroy',
            lambda node_name=node_name: destroyed.append(node_name),
        )

    monkeypatch.setattr(pipeline._nodes['mid_1'], 'destroy', _raising())

    with pytest.raises(_CleanupError):
        pipeline.destroy()

    assert destroyed == ['sink_1', 'source_1']
    assert pipeline.status['self'] == 'pipeline_destroyed'
    assert _alive_workers(node_names) == []

    pipeline.destroy()  # still a no-op


def test_destroy_of_a_running_pipeline_survives_a_raising_stop(
    test_config, wait_for_condition, monkeypatch
):
    pipeline = _running_pipeline(
        'destroy_raising_stop', test_config, wait_for_condition
    )
    node_names = list(pipeline._nodes)

    monkeypatch.setattr(pipeline._nodes['mid_1'], 'stop', _raising())

    with pytest.raises(_CleanupError):
        pipeline.destroy()

    assert pipeline.status['self'] == 'pipeline_destroyed'
    assert _alive_workers(node_names) == []


def test_an_interrupted_stop_can_be_called_again(
    test_config, wait_for_condition, monkeypatch
):
    pipeline = _running_pipeline(
        'interrupted_stop', test_config, wait_for_condition
    )
    node_names = list(pipeline._nodes)
    mid = pipeline._nodes['mid_1']

    # ctrl+c while the pipeline stops
    with monkeypatch.context() as patch:
        patch.setattr(mid, 'stop', _raising(KeyboardInterrupt))

        with pytest.raises(KeyboardInterrupt):
            pipeline.stop()

    assert pipeline.status['self'] == 'pipeline_running'

    pipeline.stop()

    assert pipeline.status['self'] == 'pipeline_stopped'
    assert _alive_workers(node_names) == []

    pipeline.destroy()


def test_an_interrupted_destroy_can_be_called_again(
    test_config, wait_for_condition, monkeypatch
):
    pipeline = _running_pipeline(
        'interrupted_destroy', test_config, wait_for_condition
    )
    pipeline.stop()

    with monkeypatch.context() as patch:
        patch.setattr(
            pipeline._nodes['mid_1'], 'destroy', _raising(KeyboardInterrupt)
        )

        with pytest.raises(KeyboardInterrupt):
            pipeline.destroy()

    # sink_1 is released already, mid_1 and source_1 are not
    assert pipeline.status['self'] == 'pipeline_stopped'
    assert sorted(pipeline.status['nodes']) == ['mid_1', 'source_1']

    pipeline.destroy()

    assert pipeline.status['self'] == 'pipeline_destroyed'


# -- kill() while a stop is waiting ------------------------------------------


def test_kill_cuts_a_stop_that_waits_for_update(
    test_config, wait_for_condition, monkeypatch
):
    monkeypatch.setattr(jt.meta, 'JUTURNA_THREAD_JOIN_TIMEOUT', 0.2)

    pipeline = _running_pipeline(
        'kill_during_stop', test_config, wait_for_condition
    )
    release = _block_node(pipeline, 'sink_1', monkeypatch)

    stop_thread = threading.Thread(target=pipeline.stop)
    stop_thread.start()
    stop_thread.join(timeout=1)

    try:
        assert stop_thread.is_alive(), 'stop() must wait for update()'

        with pytest.raises(PipelineBusyError):
            pipeline.stop()

        kill_thread = threading.Thread(target=pipeline.kill)
        kill_thread.start()
        kill_thread.join(timeout=10)
        stop_thread.join(timeout=10)

        assert not kill_thread.is_alive(), 'kill() did not come back'
        assert not stop_thread.is_alive(), 'kill() did not cut the stop'
        assert pipeline.status['self'] == 'pipeline_stopped'
        assert pipeline.status['nodes']['sink_1']['health'][
            'stuck_workers'
        ] == ['_worker_sink_1']
    finally:
        release.set()

    pipeline.destroy()

    assert pipeline.status['self'] == 'pipeline_destroyed'


def test_kill_cuts_the_stop_of_a_destroy(
    test_config, wait_for_condition, monkeypatch
):
    monkeypatch.setattr(jt.meta, 'JUTURNA_THREAD_JOIN_TIMEOUT', 0.2)

    pipeline = _running_pipeline(
        'kill_during_destroy', test_config, wait_for_condition
    )
    release = _block_node(pipeline, 'sink_1', monkeypatch)

    destroy_thread = threading.Thread(target=pipeline.destroy)
    destroy_thread.start()
    destroy_thread.join(timeout=1)

    try:
        assert destroy_thread.is_alive(), 'destroy() must wait for update()'

        pipeline.kill()
        destroy_thread.join(timeout=10)

        assert not destroy_thread.is_alive(), 'kill() did not cut the destroy'
        assert pipeline.status['self'] == 'pipeline_destroyed'
    finally:
        release.set()


@pytest.mark.parametrize('operation', ['warmup', 'start'])
def test_kill_does_not_cut_other_operations(
    test_config, monkeypatch, operation
):
    pipeline = jt.components.Pipeline(
        _config(f'kill_during_{operation}', test_config['test_pipeline_folder'])
    )

    if operation == 'start':
        pipeline.warmup()

    started = threading.Event()
    release = threading.Event()
    original = getattr(pipeline, f'_{operation}')

    def slow():
        started.set()
        release.wait(timeout=5)
        original()

    monkeypatch.setattr(pipeline, f'_{operation}', slow)

    thread = threading.Thread(target=getattr(pipeline, operation))
    thread.start()

    assert started.wait(timeout=2)

    with pytest.raises(PipelineBusyError):
        pipeline.kill()

    release.set()
    thread.join(timeout=5)

    assert not thread.is_alive()

    pipeline.destroy()


def test_node_stop_is_cut_by_a_kill_signal(monkeypatch):
    monkeypatch.setattr(jt.meta, 'JUTURNA_THREAD_JOIN_TIMEOUT', 0.2)

    node = _Blocker(node_name='cut_node', pipe_name='test_pipe')
    node.start()

    for i in range(3):
        node.put(Message(creator='test_source', version=i))

    assert node.busy.wait(timeout=5)

    stop_thread = threading.Thread(target=node.stop)
    stop_thread.start()
    stop_thread.join(timeout=0.5)

    try:
        assert stop_thread.is_alive(), 'stop() must wait for update()'

        node.signal_kill()
        stop_thread.join(timeout=5)

        assert not stop_thread.is_alive(), 'the kill did not cut stop()'
        assert node.health['stuck_workers'] == ['_worker_cut_node']
        assert node._queue.empty(), 'pending messages must be discarded'
    finally:
        node.release.set()

    time.sleep(0.3)

    assert node.calls == 1


# -- a node that stopped on its own ------------------------------------------


def test_put_does_not_wait_for_a_stopped_node(monkeypatch):
    monkeypatch.setattr(jt.meta, 'JUTURNA_MAX_QUEUE_SIZE', 2)

    node = _Collector(node_name='stopped_node', pipe_name='test_pipe')
    node.start()
    node.stop()

    def fill():
        for i in range(10):
            node.put(Message(creator='test_source', version=i))

    put_thread = threading.Thread(target=fill, daemon=True)
    put_thread.start()
    put_thread.join(timeout=5)

    assert not put_thread.is_alive(), 'put() waits for a stopped node'
    assert node.seen == []


def test_stop_does_not_hang_behind_a_node_that_stopped_itself(
    test_config, wait_for_condition, monkeypatch
):
    monkeypatch.setattr(jt.meta, 'JUTURNA_MAX_QUEUE_SIZE', 2)

    config = _config('self_stopping', test_config['test_pipeline_folder'])
    config['pipeline']['nodes'][0]['configuration'] = {'rate': 50}
    config['pipeline']['nodes'][1]['configuration'] = {'delay': 0}

    pipeline = jt.components.Pipeline(config)
    pipeline.warmup()

    sink = pipeline._nodes['sink_1']
    monkeypatch.setattr(sink, 'update', lambda message, **kwargs: sink.stop())

    pipeline.start()

    assert wait_for_condition(
        lambda: sink.status == 'component_stopped'
    ), 'sink_1 did not stop itself'

    # nothing reads the queue of sink_1 any more: give the source the time
    # to send more messages than the queues hold (it cannot, when the nodes
    # before sink_1 are stuck behind it)
    source = pipeline._nodes['source_1']
    produced = source._transmitted

    wait_for_condition(
        lambda: source._transmitted >= produced + 10, timeout=3
    )

    stop_thread = threading.Thread(target=pipeline.stop, daemon=True)
    stop_thread.start()
    stop_thread.join(timeout=10)

    assert not stop_thread.is_alive(), 'stop() hangs behind sink_1'
    assert pipeline.status['self'] == 'pipeline_stopped'

    pipeline.destroy()


# -- transmit() --------------------------------------------------------------


class _Refusing:
    def put(self, message):
        raise _CleanupError('destination failed')


def test_transmit_reaches_every_destination_when_one_fails():
    sender = Node(node_name='sender', pipe_name='test_pipe')
    receiver = _Collector(node_name='receiver', pipe_name='test_pipe')

    sender.add_destination('refusing', _Refusing())
    sender.add_destination('receiver', receiver)

    message = Message(creator='sender', version=7)

    with pytest.raises(_CleanupError):
        sender.transmit(message)

    assert receiver._queue.get_nowait() is message


# -- items that are not messages ---------------------------------------------


def test_put_rejects_what_is_not_a_message(wait_for_condition, caplog):
    node = _Collector(node_name='strict_node', pipe_name='test_pipe')
    node.logger.setLevel(logging.INFO)
    node.start()

    with caplog.at_level(logging.ERROR):
        node.put({'not': 'a message'})
        node.put(None)

    node.put(Message(creator='test_source', version=3))

    try:
        assert wait_for_condition(lambda: node.seen == [3], timeout=5)
        assert node.health['rejected_items'] == 2
        assert node.health['update_failures'] == 0
        assert node._worker_thread.is_alive()
        assert 'dict from put() is not a Message' in caplog.text
    finally:
        node.stop()


def test_a_shared_queue_item_that_is_not_a_message_is_rejected(
    wait_for_condition,
):
    node = _Collector(node_name='shared_node', pipe_name='test_pipe')
    node.start()

    # another worker writes to the queue without going through put()
    node._queue.put('not a message')
    node.put(Message(creator='test_source', version=4))

    try:
        assert wait_for_condition(lambda: node.seen == [4], timeout=5)
        assert node.health['rejected_items'] == 1
        assert node._worker_thread.is_alive()
    finally:
        node.stop()


def test_a_source_item_that_is_not_a_message_is_rejected(wait_for_condition):
    node = _Collector(node_name='source_node', pipe_name='test_pipe')
    items = iter(['not a message', Message(creator='source_node', version=5)])

    node.set_source(lambda: next(items, None), by=0.05)
    node.start()

    try:
        assert wait_for_condition(lambda: node.seen == [5], timeout=5)
        assert node.health['rejected_items'] == 1
        assert node.health['source_failures'] == 0
        assert node._source_thread.is_alive()
    finally:
        node.stop()


def test_transmit_rejects_what_is_not_a_message():
    sender = Node(node_name='sender', pipe_name='test_pipe')
    receiver = _Collector(node_name='receiver', pipe_name='test_pipe')

    sender.add_destination('receiver', receiver)
    sender.transmit('not a message')

    assert sender.health['rejected_items'] == 1
    assert receiver.health['rejected_items'] == 0
    assert receiver._queue.empty()


# -- update_node() -----------------------------------------------------------


def test_update_node_checks_the_pipeline_status(
    test_config, wait_for_condition, monkeypatch
):
    pipeline = jt.components.Pipeline(
        _config('update_node', test_config['test_pipeline_folder'])
    )

    with pytest.raises(PipelineNotReadyError):
        pipeline.update_node('mid_1', 'delay', 1)

    pipeline.warmup()

    changes = list()
    monkeypatch.setattr(
        pipeline._nodes['mid_1'],
        'set_on_config',
        lambda prop, value: changes.append((prop, value)),
    )

    pipeline.update_node('mid_1', 'delay', 1)
    pipeline.update_node('missing', 'delay', 1)  # logged, not raised

    assert changes == [('delay', 1)]

    pipeline.destroy()

    with pytest.raises(PipelineDestroyedError):
        pipeline.update_node('mid_1', 'delay', 2)
