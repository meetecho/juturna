import copy
import json
import pathlib

import pytest

import juturna as jt
from juturna.cli.commands.exceptions import TelemetryNotEnabledException
from juturna.components._pipeline_manager import PipelineManager
from juturna.telemetry.csv import CsvTelemetry
from juturna.telemetry.memory import MemoryTelemetry

with open(pathlib.Path('./tests/test_pipelines/test_empty_pipeline.json')) as f:
    _EMPTY = json.load(f)


def _pipeline(telemetry=None, transport=None):
    config = copy.deepcopy(_EMPTY)

    if telemetry is not None:
        config['pipeline']['telemetry'] = telemetry

    if transport is not None:
        config['pipeline']['transport'] = transport

    return jt.components.Pipeline(config)


@pytest.fixture
def manager():
    manager = PipelineManager()

    yield manager

    manager._pipelines.clear()


def test_telemetry_is_off_without_the_key():
    pipeline = _pipeline()
    pipeline.warmup()

    assert pipeline._telemetry_manager is None, 'Expected no manager'
    assert pipeline._telemetry is False, 'Expected telemetry off'


def test_telemetry_is_off_with_a_null_key():
    config = copy.deepcopy(_EMPTY)
    config['pipeline']['telemetry'] = None
    pipeline = jt.components.Pipeline(config)
    pipeline.warmup()

    assert pipeline._telemetry_manager is None, 'Expected no manager'


def test_memory_manager_is_built_from_the_config():
    pipeline = _pipeline({'name': 'memory'})
    pipeline.warmup()

    assert isinstance(pipeline._telemetry_manager, MemoryTelemetry), (
        f'Got {type(pipeline._telemetry_manager)}'
    )
    assert pipeline._telemetry is True, 'Expected telemetry on'


def test_csv_manager_writes_in_the_pipeline_folder():
    pipeline = _pipeline({'name': 'csv', 'target': 'tele.csv'})
    pipeline.warmup()

    manager = pipeline._telemetry_manager
    assert isinstance(manager, CsvTelemetry), f'Got {type(manager)}'
    assert manager._target == pathlib.Path(pipeline.pipe_path, 'tele.csv'), (
        f'Unexpected target {manager._target}'
    )


def test_old_string_form_fails_at_warmup():
    pipeline = _pipeline('tele.csv')

    with pytest.raises(ValueError, match='"name"'):
        pipeline.warmup()


def test_incompatible_manager_fails_at_warmup():
    pipeline = _pipeline({'name': 'csv', 'target': 'tele.csv'}, 'browser')

    with pytest.raises(ValueError, match='shared_fs'):
        pipeline.warmup()


def test_endpoint_returns_the_records_of_the_manager(manager):
    pipeline = _pipeline({'name': 'memory'})
    pipeline.warmup()
    pipeline._telemetry_manager.record_telemetry(
        [(1.0, 'tx', 'a', 'a', 1, None, 5)]
    )
    manager._pipelines[pipeline.pipe_id] = pipeline

    records = manager.pipeline_telemetry(pipeline.pipe_id)

    assert records == [(1.0, 'tx', 'a', 'a', 1, None, 5, 'main')], (
        f'Unexpected records {records}'
    )


def test_endpoint_without_telemetry(manager):
    pipeline = _pipeline()
    pipeline.warmup()
    manager._pipelines[pipeline.pipe_id] = pipeline

    with pytest.raises(TelemetryNotEnabledException):
        manager.pipeline_telemetry(pipeline.pipe_id)


def test_running_pipeline_records_telemetry(test_config, wait_for_condition):
    config = {
        'version': '0.2.0',
        'pipeline': {
            'name': 'telemetry_e2e',
            'id': 'telemetry_e2e_1',
            'folder': f'{test_config["test_pipeline_folder"]}/telemetry_e2e',
            'telemetry': {'name': 'memory'},
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

    pipeline = jt.components.Pipeline(config)
    pipeline.warmup()
    pipeline.start()

    assert wait_for_condition(
        lambda: len(pipeline._nodes['sink_1'].messages) == 4, timeout=15
    ), 'The sink did not receive the 4 messages'

    pipeline.stop()

    records = pipeline._telemetry_manager.records()
    events = [(r[2], r[1]) for r in records]

    assert events.count(('source_1', 'tx')) == 4, f'Unexpected {events}'
    assert events.count(('sink_1', 'rx')) == 4, f'Unexpected {events}'
    assert {r[-1] for r in records} == {'main'}, f'Unexpected {records}'


@pytest.mark.parametrize(
    'telemetry',
    [
        'tele.csv',
        {'name': 'nope'},
        {'name': 'csv', 'target': '../tele.csv'},
        {'name': 'csv', 'target': 'config.json'},
    ],
)
def test_refused_telemetry_leaves_nothing_on_disk(tmp_path, telemetry):
    folder = tmp_path / 'pipe'
    config = copy.deepcopy(_EMPTY)
    config['pipeline']['folder'] = str(folder)
    config['pipeline']['telemetry'] = telemetry
    pipeline = jt.components.Pipeline(config)

    with pytest.raises(ValueError):
        pipeline.warmup()

    assert not folder.exists(), 'the pipeline folder must not be created'
