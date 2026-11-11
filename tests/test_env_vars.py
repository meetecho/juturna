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
        'pipeline': {
            'name': 'test_env_pipeline',
            'id': '9999999999',
            'folder': str(pathlib.Path(test_config["test_pipeline_folder"], 'env_test_pipeline')),
            'nodes': [
                {
                    'name': 'test_node',
                    'type': 'contrib.jt_test.nodes.PassthroughIdentity',
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
        'pipeline': {
            'name': 'test_missing_env_pipeline',
            'id': '8888888888',
            'folder': './tests/running_pipelines/missing_env_test',
            'nodes': [
                {
                    'name': 'test_node',
                    'type': 'contrib.jt_test.nodes.PassthroughIdentity',
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


def _env_config(name: str, node_keys: dict) -> dict:
    return {
        'version': '0.1.0',
        'pipeline': {
            'name': name,
            'id': name,
            'folder': str(pathlib.Path(test_pipeline_folder, name)),
            'nodes': [
                {
                    'name': 'test_node',
                    'type': 'contrib.jt_test.nodes.PassthroughIdentity',
                    'configuration': {},
                    **node_keys,
                }
            ],
            'links': [],
        },
    }


def test_any_env_var_is_read_without_a_list(test_config):
    config = _env_config(
        'env_no_list', {'configuration': {'delay': '$JT_ENV_TEST_DELAY'}}
    )
    pipeline = jt.components.Pipeline(config)

    pipeline.warmup()

    assert pipeline._nodes['test_node']._delay == 2

    pipeline.destroy()


def test_env_var_in_the_list_is_read(test_config):
    config = _env_config(
        'env_in_list', {'configuration': {'delay': '$JT_ENV_TEST_DELAY'}}
    )
    pipeline = jt.components.Pipeline(config, allowed_env_vars=['TEST_DELAY'])

    pipeline.warmup()

    assert pipeline._nodes['test_node']._delay == 2

    pipeline.destroy()


@pytest.mark.parametrize(
    'node_keys',
    [
        {'configuration': {'delay': '$JT_ENV_TEST_DELAY'}},
        {
            'warped': True,
            'warp_configuration': {'grpc_host': '$JT_ENV_TEST_DELAY'},
        },
    ],
    ids=['configuration', 'warp_configuration'],
)
def test_env_var_out_of_the_list_is_refused_before_anything_is_written(
    test_config, node_keys
):
    from juturna.components.exceptions import EnvVarNotAllowedError

    config = _env_config('env_out_of_list', node_keys)

    with pytest.raises(EnvVarNotAllowedError) as error:
        jt.components.Pipeline(config, allowed_env_vars=['OTHER'])

    assert error.value.var_name == 'TEST_DELAY'
    assert error.value.node_name == 'test_node'
    assert not pathlib.Path(test_pipeline_folder, 'env_out_of_list').exists()


def test_builder_refuses_an_env_var_out_of_the_list():
    from juturna.components._node_builder import _builder
    from juturna.components.exceptions import EnvVarNotAllowedError

    node = {
        'name': 'test_node',
        'type': 'contrib.jt_test.nodes.PassthroughIdentity',
        'configuration': {'delay': '$JT_ENV_TEST_DELAY'},
    }

    with pytest.raises(EnvVarNotAllowedError):
        _builder._get_node(node, pipe_name='p', allowed_env_vars=frozenset())

    built = _builder._get_node(
        node, pipe_name='p', allowed_env_vars=frozenset({'TEST_DELAY'})
    )

    assert built._delay == 2


def test_warp_configuration_cannot_read_an_env_var_out_of_the_list(
    test_config, monkeypatch
):
    # the check before the build is taken away: the builder alone has to
    # refuse the value when the warp is built from warp_configuration
    from juturna.components._node_builder import _builder
    from juturna.components.exceptions import EnvVarNotAllowedError

    built = list()

    class Warp(jt.components.Node):
        def __init__(self, grpc_host, remote_config, sticky, **kwargs):
            super().__init__(**kwargs)

            built.append(grpc_host)

    arguments = {'grpc_host': 'localhost', 'remote_config': {}, 'sticky': True}

    monkeypatch.setattr(
        _builder, '_resolve_node', lambda _: (Warp, {'arguments': arguments})
    )
    monkeypatch.setattr(
        jt.components.Pipeline, '_check_env_vars', lambda self: None
    )
    monkeypatch.setenv('WARP_SECRET', 'secret')

    config = _env_config(
        'env_warp_backstop',
        {
            'warped': True,
            'warp_configuration': {'grpc_host': '$JT_ENV_WARP_SECRET'},
        },
    )
    pipeline = jt.components.Pipeline(config, allowed_env_vars=[])

    with pytest.raises(EnvVarNotAllowedError):
        pipeline.warmup()

    assert built == []

    pipeline = jt.components.Pipeline(config, allowed_env_vars=['WARP_SECRET'])
    pipeline.warmup()

    assert built == ['secret']

    pipeline.destroy()
