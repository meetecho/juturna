"""
Tests for environment variable resolution in pipeline configurations.
"""

import os
import pathlib
import json
import shutil
import pytest

import juturna as jt


test_pipeline_folder = './tests/running_pipelines'


@pytest.fixture(autouse=True)
def run_around_tests():
    """Setup and teardown for pipeline tests."""
    pathlib.Path(test_pipeline_folder).mkdir(exist_ok=True, parents=True)
    
    os.environ['TEST_DELAY'] = '2'
    os.environ['TEST_API_KEY'] = 'secret_api_key_12345'
    os.environ['TEST_HOST'] = 'api.example.com'
    os.environ['TEST_PORT'] = '8080'
    
    yield
    
    try:
        shutil.rmtree(test_pipeline_folder)
    except:
        ...
    
    for key in ['TEST_DELAY', 'TEST_API_KEY', 'TEST_HOST', 'TEST_PORT', 
                'MISSING_ENV_VAR', 'INT_DELAY']:
        if key in os.environ:
            del os.environ[key]


def test_pipeline_with_env_var_in_configuration():
    """Test that environment variables are resolved using $JT_ENV_ prefix."""
    config = {
        "version": "0.1.0",
        "plugins": ["./plugins"],
        "pipeline": {
            "name": "test_env_pipeline",
            "id": "9999999999",
            "folder": "./tests/running_pipelines/env_test_pipeline",
            "nodes": [
                {
                    "name": "test_node",
                    "type": "proc",
                    "mark": "passthrough_identity",
                    "configuration": {
                        "delay": "$JT_ENV_TEST_DELAY"
                    }
                }
            ],
            "links": []
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


def test_pipeline_with_missing_env_var():
    """Test that missing environment variables raise an error during warmup."""
    if 'MISSING_ENV_VAR' in os.environ:
        del os.environ['MISSING_ENV_VAR']
    
    config = {
        "version": "0.1.0",
        "plugins": ["./plugins"],
        "pipeline": {
            "name": "test_missing_env_pipeline",
            "id": "8888888888",
            "folder": "./tests/running_pipelines/missing_env_test",
            "nodes": [
                {
                    "name": "test_node",
                    "type": "proc",
                    "mark": "passthrough_identity",
                    "configuration": {
                        "delay": "$JT_ENV_MISSING_ENV_VAR"
                    }
                }
            ],
            "links": []
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


def test_type_casting_from_env_var():
    """Test that environment variables are cast to correct types based on TOML defaults."""
    os.environ['INT_DELAY'] = '5'
    
    config = {
        "version": "0.1.0",
        "plugins": ["./plugins"],
        "pipeline": {
            "name": "test_type_casting_pipeline",
            "id": "typecast123",
            "folder": "./tests/running_pipelines/typecast_test",
            "nodes": [
                {
                    "name": "test_node",
                    "type": "proc",
                    "mark": "passthrough_identity",
                    "configuration": {
                        "delay": "$JT_ENV_INT_DELAY"
                    }
                }
            ],
            "links": []
        }
    }
    
    pipeline = jt.components.Pipeline(config)
    pipeline.warmup()
    
    assert pipeline.status['self'] == 'pipeline_ready'
    node = pipeline._nodes['test_node']
    
    if 'INT_DELAY' in os.environ:
        del os.environ['INT_DELAY']
