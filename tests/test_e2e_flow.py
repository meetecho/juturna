import time
import json
import shutil
import pathlib

import pytest

import numpy as np

import juturna as jt

from juturna.names import PipelineStatus


def test_simple_pipe_generated_messages(test_config):
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

    assert len(pipeline._nodes['sink_1'].messages) == 4

    for message in pipeline._nodes['sink_1'].messages:
        assert isinstance(message, jt.components.Message)
        assert isinstance(message.payload, jt.payloads.AudioPayload)


def test_simple_pipe_dumped_messages(test_config):
    p = test_config['test_pipeline_folder']

    pipeline_config = {
        'version': '0.2.0',
        'plugins': ['./tests/test_plugins'],
        "pipeline": {
            'name': 'e2e_test_pipeline_dumped_messages',
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

    for idx in range(4):
        with open(f'{p}/e2e_test_pipeline/source_1/message_{idx}.json') as f:
            message = json.load(f)

        assert 'creator' in message.keys()
        assert 'version' in message.keys()
        assert 'payload' in message.keys()

        assert 'audio' in message['payload'].keys()
        assert message['payload']['sampling_rate'] == 16_000
        assert message['payload']['channels'] == 1
        assert message['payload']['audio_format'] == 'int16'

        audio = np.asarray(message['payload']['audio'])

        assert audio.shape == (32_000, 1)


def test_simple_pipe_synchroniser(test_config):
    p = test_config['test_pipeline_folder']

    pipeline_config = {
        'version': '0.2.0',
        'plugins': ['./tests/test_plugins'],
        "pipeline": {
            'name': 'e2e_test_pipeline_synchroniser',
            'id': 'e2e_1',
            'folder': f'{p}/e2e_test_pipeline_sync',
            'nodes': [
                {
                    'name': 'source_1',
                    'type': 'source',
                    'mark': 'sequencer',
                    'configuration': {
                        'sample_rate': 100
                    }
                },
                {
                    'name': 'proc_1',
                    'type': 'proc',
                    'mark': 'aggregator',
                    'configuration': {}
                }
            ],
            'links': [{'from': 'source_1', 'to': 'proc_1'}]
        }
    }

    pipeline = jt.components.Pipeline(pipeline_config)
    pipeline.warmup()

    pipeline.start()
    time.sleep(5)
    pipeline.stop()

    with open(f'{p}/e2e_test_pipeline_sync/proc_1/batch_0.json') as f:
        dump = json.load(f)

    assert len(dump['payload']) == 3
