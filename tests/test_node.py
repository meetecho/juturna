import time

import juturna as jt


def test_data_source_id_properly_set(test_config):
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
    time.sleep(5)
    pipeline.stop()

    out_messages = pipeline._nodes['sink_1'].messages

    assert len(pipeline._nodes['sink_1'].messages) == 4

    assert out_messages[0]._data_source_id == 0
