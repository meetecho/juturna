import importlib.util
import pathlib

import pytest

import juturna as jt
from juturna.utils import jt_utils


test_pipeline_folder = './tests/running_pipelines'

UNSAFE_NAMES = [
    '',
    '.',
    '..',
    '../escaped',
    '../../etc/cron.d/job',
    '/abs/path',
    'a/b',
    'a\\b',
    '.hidden',
    '-flag',
    'with space',
    'nul\x00byte',
    'x' * 129,
    None,
    3,
]


@pytest.mark.parametrize(
    'name', ['src', '0_src', 'my-node', 'telemetry.csv', 'x' * 128]
)
def test_check_name_accepts_plain_names(name):
    assert jt_utils.check_name(name, 'node') == name


@pytest.mark.parametrize('name', UNSAFE_NAMES)
def test_check_name_rejects_unsafe_names(name):
    with pytest.raises(ValueError, match='invalid node name'):
        jt_utils.check_name(name, 'node')


def _config(name: str, node_name: str = 'node', telemetry=None) -> dict:
    pipeline = {
        'name': name,
        'id': name,
        'folder': f'{test_pipeline_folder}/{name}',
        'nodes': [
            {
                'name': node_name,
                'type': 'contrib.jt_test.nodes.PassthroughIdentity',
                'configuration': {},
            }
        ],
        'links': [],
    }

    if telemetry:
        pipeline['telemetry'] = telemetry

    return {'version': '3.0.0', 'pipeline': pipeline}


def test_warmup_rejects_node_name_escaping_the_folder():
    pipeline = jt.components.Pipeline(
        _config('unsafe_node_pipeline', node_name='../escaped')
    )

    with pytest.raises(ValueError, match='invalid node name'):
        pipeline.warmup()

    # rejected before anything is written
    assert not pathlib.Path(test_pipeline_folder, 'escaped').exists()
    assert not pathlib.Path(
        test_pipeline_folder, 'unsafe_node_pipeline'
    ).exists()
    assert pipeline.status['self'] == 'pipeline_created'


def test_warmup_rejects_telemetry_file_escaping_the_folder():
    pipeline = jt.components.Pipeline(
        _config('unsafe_telemetry_pipeline', telemetry='../telemetry.csv')
    )

    with pytest.raises(ValueError, match='invalid telemetry file name'):
        pipeline.warmup()

    assert not pathlib.Path(test_pipeline_folder, 'telemetry.csv').exists()


def test_warmup_accepts_plain_names():
    pipeline = jt.components.Pipeline(
        _config('safe_pipeline', node_name='0_src', telemetry='telemetry.csv')
    )

    pipeline.warmup()

    assert pathlib.Path(test_pipeline_folder, 'safe_pipeline', '0_src').is_dir()

    pipeline.destroy()


@pytest.fixture
def service_client():
    # the service needs the httpwrapper extra, which CI does not install, and
    # the starlette test client needs httpx2 (or httpx)
    pytest.importorskip('fastapi')

    if not any(importlib.util.find_spec(m) for m in ('httpx2', 'httpx')):
        pytest.skip('the starlette test client needs httpx2')

    from fastapi.testclient import TestClient

    from juturna.cli.commands._juturna_service import app
    from juturna.components._pipeline_manager import PipelineManager

    PipelineManager.set_base_folder(test_pipeline_folder)

    return TestClient(app)


@pytest.mark.parametrize('endpoint', ['new', 'deploy'])
@pytest.mark.parametrize(
    'name, node_name, telemetry',
    [
        ('../../escaped', 'node', None),
        ('/abs/escaped', 'node', None),
        ('service_pipe', '../escaped', None),
        ('service_pipe', 'node', '../../id_rsa'),
    ],
)
def test_service_rejects_unsafe_names(
    service_client, endpoint, name, node_name, telemetry
):
    config = _config(name, node_name=node_name, telemetry=telemetry)
    response = service_client.post(f'/pipelines/{endpoint}', json=config)

    assert response.status_code == 422
    assert 'invalid' in response.text


def test_service_creates_pipeline_under_the_base_folder(service_client):
    from juturna.components._pipeline_manager import PipelineManager

    response = service_client.post(
        '/pipelines/new', json=_config('service_safe_pipe')
    )

    assert response.status_code == 200

    pipe_id = response.json()['data']['pipeline_id']
    folder = pathlib.Path(PipelineManager()._pipelines[pipe_id].pipe_path)

    assert (
        folder.resolve().parent
        == pathlib.Path(PipelineManager().base_folder).resolve()
    )

    service_client.post(f'/pipelines/{pipe_id}/delete?wipe=true')


def test_manager_rejects_unsafe_name_without_the_model_check(service_client):
    from juturna.cli.commands.models.api import PipelineConfig
    from juturna.components._pipeline_manager import PipelineManager

    # model_construct skips validation, as a direct caller of the manager could
    config = PipelineConfig.model_construct(**_config('../escaped'))

    with pytest.raises(ValueError, match='invalid pipeline name'):
        PipelineManager().create_pipeline(config)
