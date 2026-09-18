import pathlib
import shutil
import json

import pytest

import juturna as jt
from juturna.components import (
    PipelineAlreadyRunningError,
    PipelineStoppedError,
    PipelineDestroyedError,
)


test_pipelines = './tests/test_pipelines/'
test_pipeline_folder = './tests/running_pipelines'

with open(pathlib.Path(test_pipelines, 'test_empty_pipeline.json'), 'r') as f:
    empty_config = json.load(f)

with open(pathlib.Path(test_pipelines, 'test_audio_pipeline.json'), 'r') as f:
    audio_config = json.load(f)

with open(pathlib.Path(test_pipelines, 'test_cyclic_pipeline.json'), 'r') as f:
    cyclic_config = json.load(f)


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


def test_cyclic_pipeline_is_rejected_at_warmup():
    test_pipeline = jt.components.Pipeline(cyclic_config)

    with pytest.raises(ValueError, match='cycle'):
        test_pipeline.warmup()


def test_pipeline_warmup_is_idempotent_loopback():
    test_pipeline = jt.components.Pipeline(empty_config)

    test_pipeline.warmup()
    test_pipeline.warmup()

    assert test_pipeline.status['self'] == 'pipeline_ready'


def _sequencer_crasher_config(name: str, folder: str) -> dict:
    return {
        'version': '0.2.0',
        'plugins': ['./tests/test_plugins'],
        'pipeline': {
            'name': name,
            'id': name,
            'folder': f'{folder}/{name}',
            'nodes': [
                {
                    'name': 'source_1',
                    'type': 'source',
                    'mark': 'sequencer',
                    'configuration': {},
                },
                {
                    'name': 'sink_1',
                    'type': 'sink',
                    'mark': 'crasher',
                    'configuration': {},
                },
            ],
            'links': [{'from': 'source_1', 'to': 'sink_1'}],
        },
    }


def test_pipeline_full_lifecycle_transitions(test_config, wait_for_condition):
    folder = test_config['test_pipeline_folder']
    pipeline = jt.components.Pipeline(
        _sequencer_crasher_config('lifecycle_pipeline', folder)
    )

    pipeline.warmup()
    pipeline.start()
    pipeline.start()  # loopback: no-op, still running

    assert pipeline.status['self'] == 'pipeline_running'

    assert wait_for_condition(
        lambda: len(pipeline._nodes['sink_1'].messages) > 0
    ), 'expected sink_1 to receive at least one message'

    with pytest.raises(PipelineAlreadyRunningError):
        pipeline.warmup()

    pipeline.stop()
    pipeline.stop()  # loopback: no-op, still stopped

    assert pipeline.status['self'] == 'pipeline_stopped'

    with pytest.raises(PipelineStoppedError):
        pipeline.start()

    with pytest.raises(PipelineStoppedError):
        pipeline.warmup()

    pipeline.destroy()
    pipeline.destroy()  # loopback: no-op, still destroyed

    assert pipeline.status['self'] == 'pipeline_destroyed'

    with pytest.raises(PipelineDestroyedError):
        pipeline.start()

    with pytest.raises(PipelineDestroyedError):
        pipeline.stop()

    with pytest.raises(PipelineDestroyedError):
        pipeline.warmup()
