import time

import juturna as jt

def test_data_source_id_properly_set(test_config, wait_for_condition):
    p = test_config['test_pipeline_folder']

    pipeline_config = {
        'version': '0.2.0',
        'plugins': ['./tests/test_plugins'],
        "pipeline": {
            'name': 'e2e_test_pipeline_generated_messages',
            'id': 'e2e_1',
            'folder': f'{p}/e2e_test_pipeline',
            'nodes': [
                {
                    'name': 'source_1',
                    'type': 'source',
                    'mark': 'sequencer',
                    'configuration': {}
                },
                {
                    'name': 'sink_1',
                    'type': 'sink',
                    'mark': 'crasher',
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
        'plugins': ['./tests/test_plugins', './plugins'],
        "pipeline": {
            "name": "e2e_test_draining_pipeline",
            "id": "e2e_2",
            "folder": f'{p}/e2e_test_draining_pipeline',
            "nodes": [
                {
                    "name": "0_stream",
                    "type": "source",
                    "mark": "data_streamer",
                    "configuration": { "rate": 2 }
                },
                {
                    "name": "1_pass",
                    "type": "proc",
                    "mark": "passthrough_identity",
                    "configuration": { "delay": 2 }
                },
                {
                    'name': '2_sink',
                    'type': 'sink',
                    'mark': 'crasher',
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
        'plugins': ['./tests/test_plugins', './plugins'],
        "pipeline": {
            "name": "e2e_test_draining_pipeline",
            "id": "e2e_2",
            "folder": f'{p}/e2e_test_draining_pipeline',
            "nodes": [
                {
                    "name": "0_stream",
                    "type": "source",
                    "mark": "data_streamer",
                    "configuration": { "rate": 2 }
                },
                {
                    "name": "1_pass",
                    "type": "proc",
                    "mark": "passthrough_identity",
                    "configuration": { "delay": 2 }
                },
                {
                    'name': '2_sink',
                    'type': 'sink',
                    'mark': 'crasher',
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
        node.stop()

    received_messages = pipeline._nodes['2_sink'].messages
    received_count = len(received_messages)

    assert received_count < sent_count, (
        f"Immediate stop failed: the pipe waits for all the {sent_count} messages to be processed before stopping."
    )


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
    assert node._update_thread.is_alive()
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
