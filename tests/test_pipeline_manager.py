import pathlib
import threading

import pytest

import juturna as jt


# the manager uses the service models and exceptions, which need the
# httpwrapper extra
pytest.importorskip('fastapi')

from juturna.cli.commands._pipeline_manager import PipelineManager
from juturna.cli.commands.models.api import PipelineConfig


test_pipeline_folder = './tests/running_pipelines'

_NODE_TYPE = 'contrib.jt_test.nodes.PassthroughIdentity'


def _config(name: str, node_type: str = _NODE_TYPE, **pipeline) -> dict:
    return {
        'version': '3.0.0',
        'pipeline': {
            'name': name,
            'nodes': [
                {'name': 'node', 'type': node_type, 'configuration': {}}
            ],
            'links': [],
            **pipeline,
        },
    }


@pytest.fixture
def manager():
    PipelineManager.set_base_folder(test_pipeline_folder)
    manager = PipelineManager()

    yield manager

    manager.cleanup()


def _create(manager, name: str) -> str:
    created = manager.create_pipeline(PipelineConfig(**_config(name)))

    return created.pipeline_id


def test_cleanup_releases_pipelines_in_every_status(manager):
    new_id = _create(manager, 'cleanup_new')
    ready_id = _create(manager, 'cleanup_ready')
    running_id = _create(manager, 'cleanup_running')

    manager.warmup_pipeline(ready_id)
    manager.warmup_pipeline(running_id)
    manager.start_pipeline(running_id)

    pipelines = [manager._pipelines[i] for i in (new_id, ready_id, running_id)]

    manager.cleanup()

    assert len(manager) == 0, 'Expected an empty registry'

    for pipeline in pipelines:
        assert pipeline.status['self'] == 'pipeline_destroyed', (
            f'{pipeline.name} is {pipeline.status["self"]}'
        )


def test_cleanup_goes_on_when_a_pipeline_fails(manager, monkeypatch):
    failing_id = _create(manager, 'cleanup_failing')
    other_id = _create(manager, 'cleanup_other')
    other = manager._pipelines[other_id]

    def _fail():
        raise RuntimeError('destroy failed')

    monkeypatch.setattr(manager._pipelines[failing_id], 'destroy', _fail)

    manager.cleanup()

    assert len(manager) == 0, 'Expected an empty registry'
    assert other.status['self'] == 'pipeline_destroyed'


@pytest.mark.parametrize('failing_step', ['warmup', 'start'])
def test_failed_deploy_leaves_nothing_behind(
    manager, monkeypatch, failing_step
):
    def _fail(self):
        raise RuntimeError(f'{failing_step} failed')

    monkeypatch.setattr(jt.components.Pipeline, failing_step, _fail)

    before = len(manager)

    with pytest.raises(RuntimeError, match=f'{failing_step} failed'):
        manager.deploy_pipeline(
            PipelineConfig(**_config(f'deploy_{failing_step}'))
        )

    assert len(manager) == before, 'The failed deploy is still registered'
    assert not list(pathlib.Path(test_pipeline_folder).glob('deploy_*')), (
        'The failed deploy left its folder'
    )


def test_failed_deploy_of_an_unknown_node_type(manager):
    before = len(manager)

    with pytest.raises(Exception):
        manager.deploy_pipeline(
            PipelineConfig(**_config('deploy_ghost', 'contrib.no.Such'))
        )

    assert len(manager) == before, 'The failed deploy is still registered'


def test_delete_keeps_a_pipeline_that_cannot_be_destroyed(
    manager, monkeypatch
):
    pipe_id = _create(manager, 'delete_failing')

    def _fail():
        raise RuntimeError('destroy failed')

    monkeypatch.setattr(manager._pipelines[pipe_id], 'destroy', _fail)

    with pytest.raises(RuntimeError):
        manager.delete_pipeline(pipe_id, wipe_folder=False)

    assert pipe_id in manager._pipelines


def test_concurrent_calls_on_the_registry(manager):
    errors = []
    stop = threading.Event()

    def _churn(idx):
        try:
            for i in range(30):
                pipe_id = _create(manager, f'churn_{idx}_{i}')
                manager.delete_pipeline(pipe_id, wipe_folder=True)
        except Exception as exc:
            errors.append(exc)

    def _list():
        try:
            while not stop.is_set():
                manager.pipeline_list()
        except Exception as exc:
            errors.append(exc)

    readers = [threading.Thread(target=_list) for _ in range(4)]
    writers = [threading.Thread(target=_churn, args=(i,)) for i in range(4)]

    for thread in readers + writers:
        thread.start()

    for thread in writers:
        thread.join()

    stop.set()

    for thread in readers:
        thread.join()

    assert errors == [], f'Concurrent calls failed: {errors[:3]}'


def test_status_skips_the_nodes_already_destroyed():
    config = _config('status_destroying')
    config['pipeline'] |= {
        'id': 'status_destroying',
        'folder': f'{test_pipeline_folder}/status_destroying',
    }

    pipeline = jt.components.Pipeline(config)
    pipeline.warmup()

    # what a status request sees halfway through destroy()
    nodes = pipeline._nodes
    pipeline._nodes = {'node': None}

    assert pipeline.status['nodes'] == {}

    pipeline._nodes = nodes
    pipeline.destroy()

    assert pipeline.status['nodes'] == {}


def test_service_shutdown_releases_the_pipelines(service_app):
    from fastapi.testclient import TestClient

    from tests.conftest import SERVICE_TOKEN

    headers = {'Authorization': f'Bearer {SERVICE_TOKEN}'}

    with TestClient(service_app, headers=headers) as client:
        response = client.post(
            '/pipelines/deploy', json=_config('shutdown_running')
        )

        assert response.status_code == 200, response.text

        pipeline = PipelineManager()._pipelines[response.json()['pipe_id']]

    assert pipeline.status['self'] == 'pipeline_destroyed'
    assert len(PipelineManager()) == 0


@pytest.mark.parametrize(
    'pipeline',
    [
        {'nodes': None},
        {'nodes': ['node']},
        {'nodes': [{'name': 'node', 'configuration': {}}]},
        {'nodes': [{'name': 'node', 'type': _NODE_TYPE}]},
        {
            'nodes': [
                {'name': 'node', 'type': _NODE_TYPE, 'configuration': {}},
                {'name': 'node', 'type': _NODE_TYPE, 'configuration': {}},
            ]
        },
        {'links': None},
        {'links': [{'from': 'node'}]},
        {'links': [['node', 'node']]},
        {'transport': 'pigeon'},
        {'log_extra': 'x'},
    ],
)
def test_service_rejects_malformed_pipelines(service_client, pipeline):
    config = _config('malformed')
    config['pipeline'] |= pipeline

    for endpoint in ('new', 'deploy'):
        response = service_client.post(f'/pipelines/{endpoint}', json=config)

        assert response.status_code == 422, (
            f'{endpoint} answered {response.status_code}: {response.text}'
        )


def test_from_json_uses_the_worker(tmp_path):
    path = tmp_path / 'config.json'
    path.write_text(
        '{"pipeline": {"name": "p", "id": "p", "folder": "x", '
        '"nodes": [], "links": []}}'
    )

    pipeline = jt.components.Pipeline.from_json(str(path), worker='gpu')

    assert pipeline._worker == 'gpu'
