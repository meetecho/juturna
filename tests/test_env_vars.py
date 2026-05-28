import os
import pathlib
import json
import logging

import pytest

import juturna as jt


test_pipeline_folder = './tests/running_pipelines'


@pytest.fixture(autouse=True)
def run_around_tests():
    os.environ['TEST_DELAY'] = '2'

    yield

    if 'TEST_DELAY' in os.environ:
        del os.environ['TEST_DELAY']


def test_pipeline_with_env_var_in_configuration(test_config):
    config = {
        'version': '0.1.0',
        'plugins': ['./plugins'],
        'pipeline': {
            'name': 'test_env_pipeline',
            'id': '9999999999',
            'folder': str(pathlib.Path(test_config["test_pipeline_folder"], 'env_test_pipeline')),
            'nodes': [
                {
                    'name': 'test_node',
                    'type': 'proc',
                    'mark': 'passthrough_identity',
                    'configuration': {
                        'delay': '$JT_ENV_TEST_DELAY'
                    }
                }
            ],
            'links': []
        }
    }

    pipeline = jt.components.Pipeline(config)
    pipeline.warmup()

    assert pipeline.status['self'] == 'pipeline_ready'
    assert 'test_node' in pipeline.status['nodes']

    saved_config_path = pathlib.Path(test_pipeline_folder, 'env_test_pipeline', 'config.json')
    assert saved_config_path.exists()

    with open(saved_config_path, 'r') as f:
        saved_config = json.load(f)

    assert saved_config['pipeline']['nodes'][0]['configuration']['delay'] == '$JT_ENV_TEST_DELAY'

    assert pipeline._nodes['test_node']._delay == 2


def test_pipeline_with_missing_env_var(test_config, caplog):
    caplog.set_level(logging.CRITICAL, logger='jt.builder')

    if 'MISSING_ENV_VAR' in os.environ:
        del os.environ['MISSING_ENV_VAR']

    config = {
        'version': '0.1.0',
        'plugins': ['./plugins'],
        'pipeline': {
            'name': 'test_missing_env_pipeline',
            'id': '8888888888',
            'folder': './tests/running_pipelines/missing_env_test',
            'nodes': [
                {
                    'name': 'test_node',
                    'type': 'proc',
                    'mark': 'passthrough_identity',
                    'configuration': {
                        'delay': '$JT_ENV_MISSING_ENV_VAR'
                    }
                }
            ],
            'links': []
        }
    }

    pipeline = jt.components.Pipeline(config)

    with pytest.raises(ValueError) as exc_info:
        pipeline.warmup()

    error_message = str(exc_info.value)

    assert 'MISSING_ENV_VAR' in error_message
    assert 'not set' in error_message.lower()
    assert 'test_node' in error_message or 'node "test_node"' in error_message
    assert 'delay' in error_message or 'config key "delay"' in error_message
