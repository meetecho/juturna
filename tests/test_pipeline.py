import pathlib
import shutil
import json
import threading

import pytest

import juturna as jt
from juturna.components import (
    PipelineAlreadyRunningError,
    PipelineStoppedError,
    PipelineDestroyedError,
    PipelineBusyError,
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


def test_pipeline_status_reflects_completion_not_claim(monkeypatch):
    test_pipeline = jt.components.Pipeline(empty_config)

    started = threading.Event()
    release = threading.Event()
    original_warmup = test_pipeline._warmup

    def slow_warmup():
        started.set()
        release.wait(timeout=5)
        original_warmup()

    monkeypatch.setattr(test_pipeline, '_warmup', slow_warmup)

    warmup_thread = threading.Thread(target=test_pipeline.warmup)
    warmup_thread.start()

    assert started.wait(timeout=2), 'warmup() did not start in time'

    # the transition is claimed but the work is not finished yet: status
    # must still be NEW, not the target READY
    assert test_pipeline.status['self'] == 'pipeline_created'

    # a concurrent lifecycle call must be rejected deterministically,
    # instead of racing against the not-yet-real target status
    with pytest.raises(PipelineBusyError):
        test_pipeline.start()

    release.set()
    warmup_thread.join(timeout=5)

    assert not warmup_thread.is_alive()
    assert test_pipeline.status['self'] == 'pipeline_ready'


def test_pipeline_concurrent_stop_is_rejected_not_duplicated(
    test_config, wait_for_condition, monkeypatch
):
    folder = test_config['test_pipeline_folder']
    pipeline = jt.components.Pipeline(
        _sequencer_crasher_config('concurrent_stop_pipeline', folder)
    )

    pipeline.warmup()
    pipeline.start()

    assert wait_for_condition(
        lambda: len(pipeline._nodes['sink_1'].messages) > 0
    ), 'expected sink_1 to receive at least one message'

    started = threading.Event()
    release = threading.Event()
    call_count = {'n': 0}
    original_stop = pipeline._stop

    def slow_stop():
        call_count['n'] += 1
        started.set()
        release.wait(timeout=5)
        original_stop()

    monkeypatch.setattr(pipeline, '_stop', slow_stop)

    stop_thread = threading.Thread(target=pipeline.stop)
    stop_thread.start()

    assert started.wait(timeout=2), 'stop() did not start in time'

    # a second, concurrent stop() must not re-enter _stop() while the
    # first one is still draining nodes
    with pytest.raises(PipelineBusyError):
        pipeline.stop()

    release.set()
    stop_thread.join(timeout=5)

    assert not stop_thread.is_alive()
    assert call_count['n'] == 1, '_stop() must run exactly once'
    assert pipeline.status['self'] == 'pipeline_stopped'

    pipeline.destroy()


def test_pipeline_destroy_while_running_stops_then_destroys(
    test_config, wait_for_condition
):
    folder = test_config['test_pipeline_folder']
    pipeline = jt.components.Pipeline(
        _sequencer_crasher_config('destroy_while_running_pipeline', folder)
    )

    pipeline.warmup()
    pipeline.start()

    assert wait_for_condition(
        lambda: len(pipeline._nodes['sink_1'].messages) > 0
    ), 'expected sink_1 to receive at least one message'

    pipeline.destroy()

    assert pipeline.status['self'] == 'pipeline_destroyed'
