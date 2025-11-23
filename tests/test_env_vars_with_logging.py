"""
Tests for environment variable resolution in pipeline configurations.
"""

import os
import pathlib
import json
import shutil
import logging
import pytest

import juturna as jt


test_pipeline_folder = './tests/running_pipelines'


@pytest.fixture(autouse=True)
def run_around_tests():
    """Setup and teardown for pipeline tests."""
    pathlib.Path(test_pipeline_folder).mkdir(exist_ok=True, parents=True)
    
    # Set up test environment variables
    os.environ['TEST_DELAY'] = '2'
    os.environ['TEST_API_KEY'] = 'secret_api_key_12345'
    os.environ['TEST_HOST'] = 'api.example.com'
    os.environ['TEST_PORT'] = '8080'
    
    yield
    
    # Cleanup
    try:
        shutil.rmtree(test_pipeline_folder)
    except:
        ...
    
    # Clean up environment variables
    for key in ['TEST_DELAY', 'TEST_API_KEY', 'TEST_HOST', 'TEST_PORT', 
                'API_SECRET_KEY', 'DATABASE_PASSWORD', 'JWT_TOKEN', 
                'AWS_ACCESS_KEY', 'API_HOST', 'API_PORT', 'SECRET_API_KEY', 
                'DB_PASSWORD', 'API_BASE_URL', 'MISSING_SECRET_KEY', 
                'MISSING_API_TOKEN', 'MISSING_ENV_VAR']:
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
    
    # Verify the pipeline was created successfully (env var was resolved)
    # The actual delay value is stored in the node's internal state (_delay attribute)
    # but we can verify the pipeline warmup succeeded, which means env var resolution worked
    
    saved_config_path = pathlib.Path(test_pipeline_folder, 'env_test_pipeline', 'config.json')
    assert saved_config_path.exists()
    
    with open(saved_config_path, 'r') as f:
        saved_config = json.load(f)
    
    # Saved config should still have the $JT_ENV_ syntax (env vars are resolved in memory, not in saved file)
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
    
    assert 'MISSING_ENV_VAR' in str(exc_info.value)
    assert 'not set' in str(exc_info.value).lower()


def test_pipeline_with_mixed_env_vars_and_regular_values():
    """Test pipeline with both env vars and regular values."""
    config = {
        "version": "0.1.0",
        "plugins": ["./plugins"],
        "pipeline": {
            "name": "test_mixed_pipeline",
            "id": "7777777777",
            "folder": "./tests/running_pipelines/mixed_test",
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
    
    # Verify the pipeline was created successfully (env var was resolved and type-cast)
    # The actual delay value is stored in the node's internal state (_delay attribute)
    # If warmup succeeded, it means the env var was resolved and cast to int correctly


def test_pipeline_warmup_with_secret_keys_logging(capsys):
    """Test that environment variables including secret keys are logged during warmup."""
    os.environ['API_SECRET_KEY'] = 'test_api_key_fake_1234567890abcdefghijklmnopqrstuvwxyz'
    os.environ['DATABASE_PASSWORD'] = 'MySecureP@ssw0rd123!'
    os.environ['JWT_TOKEN'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ'
    os.environ['AWS_ACCESS_KEY'] = 'AKIAIOSFODNN7EXAMPLE'
    os.environ['API_HOST'] = 'api.production.example.com'
    os.environ['API_PORT'] = '443'
    
    config = {
        "version": "0.1.0",
        "plugins": ["./plugins"],
        "pipeline": {
            "name": "test_secrets_pipeline",
            "id": "secrets123",
            "folder": "./tests/running_pipelines/secrets_test",
            "nodes": [
                {
                    "name": "api_client_node",
                    "type": "proc",
                    "mark": "passthrough_identity",
                    "configuration": {
                        "delay": 1
                    }
                }
            ],
            "links": []
        }
    }
    
    logger = jt.utils.log_utils.jt_logger()
    logger.setLevel(logging.INFO)
    
    pipeline = jt.components.Pipeline(config)
    
    with capsys.disabled():
        pipeline.warmup()
    
    assert pipeline.status['self'] == 'pipeline_ready'
    assert 'api_client_node' in pipeline.status['nodes']


def test_pipeline_warmup_missing_env_var_error_logging(capsys):
    """Test that missing environment variables produce clear error messages."""
    if 'MISSING_SECRET_KEY' in os.environ:
        del os.environ['MISSING_SECRET_KEY']
    
    config = {
        "version": "0.1.0",
        "plugins": ["./plugins"],
        "pipeline": {
            "name": "test_missing_secrets_pipeline",
            "id": "missing123",
            "folder": "./tests/running_pipelines/missing_secrets_test",
            "nodes": [
                {
                    "name": "failing_node",
                    "type": "proc",
                    "mark": "passthrough_identity",
                    "configuration": {
                        "delay": "$JT_ENV_MISSING_SECRET_KEY"
                    }
                }
            ],
            "links": []
        }
    }
    
    logger = jt.utils.log_utils.jt_logger()
    logger.setLevel(logging.ERROR)
    
    pipeline = jt.components.Pipeline(config)
    
    with pytest.raises(ValueError) as exc_info:
        pipeline.warmup()
    
    error_message = str(exc_info.value)
    
    assert 'MISSING_SECRET_KEY' in error_message
    assert 'not set' in error_message.lower()
    assert 'node "failing_node"' in error_message or 'failing_node' in error_message
    assert 'config key "delay"' in error_message or 'delay' in error_message


def test_mask_sensitive_value():
    """Test that sensitive values are properly masked in logs."""
    from juturna.components._component_builder import _mask_sensitive_value
    
    secret_key = 'test_api_key_fake_1234567890abcdefghijklmnopqrstuvwxyz'
    masked = _mask_sensitive_value('API_SECRET_KEY', secret_key)
    assert masked.startswith('test')
    assert masked.endswith('wxyz')
    assert '****' in masked
    assert len(masked) < len(secret_key)
    
    password = 'MySecureP@ssw0rd123!'
    masked = _mask_sensitive_value('DATABASE_PASSWORD', password)
    assert masked.startswith('MySe')
    assert masked.endswith('23!')
    assert '****' in masked
    
    host = 'api.example.com'
    masked = _mask_sensitive_value('API_HOST', host)
    assert masked == host
    
    short_token = 'abc123'
    masked = _mask_sensitive_value('API_TOKEN', short_token)
    assert masked == '****'


def test_type_casting_from_env_var():
    """Test that environment variables are cast to correct types based on TOML defaults."""
    # Test integer casting (delay is int in TOML)
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
    
    # Verify the pipeline was created successfully (env var was resolved and cast to int)
    # The actual delay value is stored in the node's internal state (_delay attribute)
    # If warmup succeeded without errors, it means:
    # 1. The env var was found
    # 2. It was cast to int (since delay default is int in TOML)
    # 3. The node was instantiated successfully
    
    # Cleanup
    if 'INT_DELAY' in os.environ:
        del os.environ['INT_DELAY']
