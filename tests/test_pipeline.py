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
