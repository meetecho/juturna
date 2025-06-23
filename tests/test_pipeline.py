import pathlib
import shutil
import json

import pytest

import juturna as jt


test_pipelines = './tests/test_pipelines/'
test_pipeline_folder = './tests/running_pipelines'

with open(pathlib.Path(test_pipelines, 'test_empty_pipeline.json'), 'r') as f:
    empty_config = json.load(f)

with open(pathlib.Path(test_pipelines, 'test_audio_pipeline.json'), 'r') as f:
    audio_config = json.load(f)


@pytest.fixture(autouse=True)
def run_around_tests():
    pathlib.Path(test_pipeline_folder).mkdir(exist_ok=True, parents=True)

    yield

    try:
        shutil.rmtree(test_pipeline_folder)
    except:
        ...


def test_pipeline_base():
    test_pipeline = jt.components.Pipeline(empty_config)

    assert test_pipeline.name == 'test_basic_pipeline'
    assert test_pipeline.pipe_id == '1234567890'
    assert test_pipeline.pipe_path == './tests/running_pipelines/basic_pipeline'


def test_pipeline_from_path():
    test_pipeline = jt.components.Pipeline.from_json(
        './tests/test_pipelines/test_empty_pipeline.json')

    assert test_pipeline.name == 'test_basic_pipeline'
    assert test_pipeline.pipe_id == '1234567890'
    assert test_pipeline.pipe_path == './tests/running_pipelines/basic_pipeline'


def test_pipeline_new_status():
    test_pipeline = jt.components.Pipeline(empty_config)

    assert test_pipeline.status == {
        'pipe_id': '1234567890',
        'folder': './tests/running_pipelines/basic_pipeline',
        'self': 'pipeline_created',
        'nodes': dict()
    }


def test_pipeline_base_warmup():
    test_pipeline = jt.components.Pipeline(empty_config)

    test_pipeline.warmup()

    assert test_pipeline.status['self'] == 'pipeline_ready'

    with open('./tests/running_pipelines/basic_pipeline/config.json', 'r') as f:
        saved = json.load(f)

    assert saved == empty_config


def test_pipeline_base_start():
    test_pipeline = jt.components.Pipeline(empty_config)

    test_pipeline.warmup()
    test_pipeline.start()

    assert test_pipeline.status['self'] == 'pipeline_running'


def test_pipeline_base_stop():
    test_pipeline = jt.components.Pipeline(empty_config)

    test_pipeline.warmup()
    test_pipeline.start()
    test_pipeline.stop()

    assert test_pipeline.status['self'] == 'pipeline_ready'


def test_pipeline_base_warmup_not_new():
    test_pipeline = jt.components.Pipeline(empty_config)

    test_pipeline.warmup()
    test_pipeline.start()

    with pytest.raises(RuntimeError) as exc_info:
        test_pipeline.warmup()

    assert str(exc_info.value) == \
        'pipeline test_basic_pipeline cannot be warmed up'


def test_pipeline_base_start_not_ready():
    test_pipeline = jt.components.Pipeline(empty_config)

    with pytest.raises(RuntimeError) as exc_info:
        test_pipeline.start()

    assert str(exc_info.value) == 'pipeline test_basic_pipeline is not ready'


def test_pipeline_base_stop_not_running():
    test_pipeline = jt.components.Pipeline(empty_config)

    with pytest.raises(RuntimeError) as exc_info:
        test_pipeline.stop()

    assert str(exc_info.value) == 'pipeline test_basic_pipeline is not running'


def test_pipeline_node_config_change():
    test_pipeline = jt.components.Pipeline.from_json(
        str(pathlib.Path(test_pipelines, 'test_audio_pipeline.json')))

    test_pipeline.warmup()

    assert test_pipeline._pipe is not None

    assert test_pipeline._pipe['2_dst']['node'].configuration['endpoint'] == \
        'http://127.0.0.1:1237'
    
    test_pipeline.update_node('2_dst', 'endpoint', 'http://127.0.0.1:1238')

    assert test_pipeline._pipe['2_dst']['node'].configuration['endpoint'] == \
        'http://127.0.0.1:1238'