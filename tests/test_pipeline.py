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
        'pipeline': {
            'name': name,
            'id': name,
            'folder': f'{folder}/{name}',
            'nodes': [
                {
                    'name': 'source_1',
                    'type': 'contrib.jt_test.nodes.Sequencer',
                    'configuration': {},
                },
                {
                    'name': 'sink_1',
                    'type': 'contrib.jt_test.nodes.Crasher',
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



class _StartError(Exception):
    pass


def _alive_workers(pipeline) -> list[str]:
    names = {
        f'_{kind}_{node_name}'
        for kind in ('worker', 'update', 'source')
        for node_name in pipeline._nodes
    }

    return [t.name for t in threading.enumerate() if t.name in names]


def _failing_start(node, spawn_first: bool, error=_StartError):
    original_start = node.start

    def start():
        if spawn_first:
            original_start()

        raise error(f'{node.name} failed to start')

    return start


# an interrupt (ctrl+c while the pipeline starts) is rolled back as well
@pytest.mark.parametrize('error', [_StartError, KeyboardInterrupt])
@pytest.mark.parametrize('spawn_first', [False, True])
def test_failed_start_stops_the_nodes_already_started(
    test_config, monkeypatch, spawn_first, error
):
    folder = test_config['test_pipeline_folder']
    config = _sequencer_crasher_config(
        f'failed_start_pipeline_{spawn_first}_{error.__name__}', folder
    )
    config['pipeline']['telemetry'] = {
        'name': 'csv',
        'target': 'telemetry.csv',
    }
    pipeline = jt.components.Pipeline(config)

    pipeline.warmup()

    # sink_1 is started first, then source_1 fails (after spawning its own
    # workers, when spawn_first is set)
    source = pipeline._nodes['source_1']
    monkeypatch.setattr(
        source, 'start', _failing_start(source, spawn_first, error)
    )

    with pytest.raises(error):
        pipeline.start()

    assert pipeline.status['self'] == 'pipeline_ready'
    assert _alive_workers(pipeline) == []
    assert not pipeline._telemetry_manager._thread
    assert all(
        node['status'] == 'component_configured'
        for node in pipeline.status['nodes'].values()
    )

    pipeline.destroy()

    assert pipeline.status['self'] == 'pipeline_destroyed'


def test_start_can_be_retried_after_a_failed_start(
    test_config, monkeypatch, wait_for_condition
):
    folder = test_config['test_pipeline_folder']
    config = _sequencer_crasher_config('retry_start_pipeline', folder)
    config['pipeline']['telemetry'] = {
        'name': 'csv',
        'target': 'telemetry.csv',
    }
    pipeline = jt.components.Pipeline(config)

    pipeline.warmup()

    source = pipeline._nodes['source_1']
    monkeypatch.setattr(source, 'start', _failing_start(source, True))

    with pytest.raises(_StartError):
        pipeline.start()

    monkeypatch.undo()
    pipeline.start()

    assert pipeline.status['self'] == 'pipeline_running'
    assert wait_for_condition(
        lambda: len(pipeline._nodes['sink_1'].messages) > 0
    ), 'expected sink_1 to receive messages after the retry'

    pipeline.stop()

    with open(pathlib.Path(pipeline.pipe_path, 'telemetry.csv')) as f:
        header_rows = [line for line in f if line.startswith('ts,')]

    assert len(header_rows) == 1

    pipeline.destroy()


class _WarmupError(Exception):
    pass


def _raise(error):
    def fail(self):
        raise error(f'{self.name} failed to warm up')

    return fail


@pytest.fixture
def destroyed(monkeypatch):
    from juturna.contrib.jt_test.nodes import Crasher, Sequencer

    names = list()

    for cls in (Crasher, Sequencer):
        monkeypatch.setattr(cls, 'destroy', lambda self: names.append(self.name))

    return names


def _break_node_warmup(config, monkeypatch, error=_WarmupError):
    from juturna.contrib.jt_test.nodes import Crasher

    monkeypatch.setattr(Crasher, 'warmup', _raise(error))

    return error


def _add_unknown_node(config, monkeypatch):
    config['pipeline']['nodes'].append(
        {'name': 'ghost', 'type': 'contrib.jt_test.nodes.Missing'}
    )

    return Exception


def _add_cycle(config, monkeypatch):
    config['pipeline']['links'].append({'from': 'sink_1', 'to': 'source_1'})

    return ValueError


@pytest.mark.parametrize(
    'break_warmup',
    [
        _break_node_warmup,
        lambda c, m: _break_node_warmup(c, m, KeyboardInterrupt),
        _add_unknown_node,
        _add_cycle,
    ],
    ids=['node_warmup', 'interrupt', 'unknown_type', 'cycle'],
)
def test_failed_warmup_destroys_the_nodes_already_built(
    test_config, monkeypatch, destroyed, break_warmup
):
    config = _sequencer_crasher_config(
        'failed_warmup_pipeline', test_config['test_pipeline_folder']
    )
    config['pipeline']['telemetry'] = {
        'name': 'csv',
        'target': 'telemetry.csv',
    }
    error = break_warmup(config, monkeypatch)
    pipeline = jt.components.Pipeline(config)

    with pytest.raises(error):
        pipeline.warmup()

    assert destroyed == ['sink_1', 'source_1']
    assert pipeline.status['self'] == 'pipeline_created'
    assert pipeline.status['nodes'] == {}
    assert pipeline._dag.edges == []
    assert pipeline._telemetry_manager is None


def test_warmup_can_be_retried_after_a_failed_warmup(
    test_config, monkeypatch, destroyed
):
    config = _sequencer_crasher_config(
        'retry_warmup_pipeline', test_config['test_pipeline_folder']
    )
    pipeline = jt.components.Pipeline(config)
    _break_node_warmup(config, monkeypatch)

    with pytest.raises(_WarmupError):
        pipeline.warmup()

    monkeypatch.undo()
    pipeline.warmup()

    assert pipeline.status['self'] == 'pipeline_ready'
    assert sorted(pipeline._nodes) == ['sink_1', 'source_1']
    assert pipeline._dag.edges == [('source_1', 'sink_1')]
    assert pipeline._nodes['sink_1'].origins == ['source_1']

    pipeline.destroy()


def test_failed_warmup_leaves_the_warped_node_config_unchanged(test_config):
    config = _sequencer_crasher_config(
        'warped_warmup_pipeline', test_config['test_pipeline_folder']
    )
    config['pipeline']['nodes'][1].update(
        {'warped': True, 'warp_configuration': {'host': 'localhost'}}
    )
    pipeline = jt.components.Pipeline(config)

    # the Warp node is not shipped by core, so its build fails
    with pytest.raises(Exception):
        pipeline.warmup()

    assert pipeline._raw_config == config


@pytest.mark.parametrize(
    'link, message',
    [
        ({'from': 'source_1', 'to': 'sink_1'}, 'duplicate link source_1 -> sink_1'),
        ({'from': 'source_1', 'to': 'ghost'}, 'has no node ghost'),
        ({'from': 'ghost', 'to': 'sink_1'}, 'has no node ghost'),
    ],
    ids=['duplicate', 'unknown_destination', 'unknown_source'],
)
def test_invalid_links_are_rejected_before_building(
    test_config, destroyed, link, message
):
    config = _sequencer_crasher_config(
        'invalid_link_pipeline', test_config['test_pipeline_folder']
    )
    config['pipeline']['links'].append(link)
    pipeline = jt.components.Pipeline(config)

    with pytest.raises(ValueError, match=message):
        pipeline.warmup()

    assert destroyed == []
    assert pipeline.status['self'] == 'pipeline_created'


def test_duplicate_node_names_are_rejected_before_building(test_config):
    config = _sequencer_crasher_config(
        'duplicate_node_pipeline', test_config['test_pipeline_folder']
    )
    config['pipeline']['nodes'].append(
        {
            'name': 'source_1',
            'type': 'contrib.jt_test.nodes.Sequencer',
            'configuration': {},
        }
    )
    pipeline = jt.components.Pipeline(config)

    with pytest.raises(ValueError, match='two nodes named source_1'):
        pipeline.warmup()

    assert pipeline.status['self'] == 'pipeline_created'
    assert pipeline._nodes == {}
    assert not pathlib.Path(pipeline.pipe_path).exists(), (
        'warmup wrote the pipeline folder'
    )
