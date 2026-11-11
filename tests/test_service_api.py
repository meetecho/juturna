"""
The HTTP service as its clients see it: what is checked before a request is
handled, the answers to client mistakes, and the endpoints a frontend needs
(node catalogue, validation, configuration, files, logs).
"""

import json
import logging
import os
import pathlib

import pytest

from tests.conftest import SERVICE_TOKEN


pytest.importorskip('fastapi')

_NODE_TYPE = 'contrib.jt_test.nodes.PassthroughIdentity'
_AUTH = {'Authorization': f'Bearer {SERVICE_TOKEN}'}


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
def anonymous_client(service_app):
    from fastapi.testclient import TestClient

    return TestClient(service_app)


@pytest.fixture
def client(service_client):
    from juturna.cli.commands._pipeline_manager import PipelineManager

    yield service_client

    PipelineManager().cleanup()


def _create(client, name: str, **kwargs) -> str:
    response = client.post('/pipelines/new', json=_config(name, **kwargs))

    assert response.status_code == 200, response.text

    return response.json()['data']['pipeline_id']


# -- nothing is read before the token is checked -----------------------------


@pytest.mark.parametrize(
    'body',
    [b'{not json', b'{}', b'[1, 2]', b'x' * (2 * 1024 * 1024)],
    ids=['broken', 'incomplete', 'wrong-shape', 'huge'],
)
@pytest.mark.parametrize(
    'path', ['/pipelines/new', '/pipelines/deploy', '/pipelines/validate']
)
def test_anonymous_bodies_are_not_parsed(anonymous_client, path, body):
    response = anonymous_client.post(
        path, content=body, headers={'Content-Type': 'application/json'}
    )

    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'
    assert response.json() == {'detail': 'missing or invalid service token'}


def test_the_documentation_pages_open_with_the_token(service_client):
    for path in ('/docs', '/redoc', '/openapi.json'):
        assert service_client.get(path).status_code == 200, path


def test_a_body_over_the_limit_is_refused(service_app, service_client):
    service_app.state.max_body_bytes = 2000

    try:
        fits = service_client.post(
            '/pipelines/validate', json=_config('small')
        )
        declared = service_client.post(
            '/pipelines/validate',
            content=b' ' * 2001,
            headers={'Content-Type': 'application/json'},
        )

        # sent in chunks, so without a declared length
        chunked = service_client.post(
            '/pipelines/validate',
            content=(b' ' * 500 for _ in range(10)),
            headers={'Content-Type': 'application/json'},
        )
    finally:
        service_app.state.max_body_bytes = None

    assert fits.status_code == 200
    assert declared.status_code == 413
    assert 'transfer-encoding' in chunked.request.headers
    assert chunked.status_code == 413
    assert 'larger than 2000 bytes' in chunked.json()['detail']


def test_the_default_body_limit(service_client):
    response = service_client.post(
        '/pipelines/new',
        content=b' ' * (1024 * 1024 + 1),
        headers={'Content-Type': 'application/json'},
    )

    assert response.status_code == 413


# -- client mistakes get a 4xx that says what is wrong -----------------------


def _two_nodes(**second) -> list[dict]:
    return [
        {'name': 'a', 'type': _NODE_TYPE, 'configuration': {}},
        {'name': 'b', 'type': _NODE_TYPE, 'configuration': {}, **second},
    ]


@pytest.mark.parametrize(
    ('change', 'reason'),
    [
        ({'nodes': []}, 'cannot be empty'),
        (
            {'links': [{'from': 'node', 'to': 'ghost'}]},
            'has no node ghost',
        ),
        (
            {
                'nodes': _two_nodes(),
                'links': [{'from': 'a', 'to': 'b'}] * 2,
            },
            'duplicate link',
        ),
        (
            {'nodes': _two_nodes(warped=True)},
            'is warped: it needs a',
        ),
        (
            {'nodes': _two_nodes(warped=True, warp_configuration='x')},
            'is warped: it needs a',
        ),
    ],
    ids=['no-nodes', 'unknown-link', 'duplicate-link', 'warp', 'warp-shape'],
)
@pytest.mark.parametrize('path', ['/pipelines/new', '/pipelines/deploy'])
def test_a_wrong_pipeline_is_refused_before_it_is_created(
    client, path, change, reason
):
    before = client.get('/pipelines').json()

    response = client.post(path, json=_config('wrong', **change))

    assert response.status_code == 422, response.text
    assert reason in response.text
    assert client.get('/pipelines').json() == before


@pytest.mark.parametrize('version', ['', '  '])
def test_an_empty_version_is_refused(client, version):
    config = {**_config('no_version'), 'version': version}

    assert client.post('/pipelines/new', json=config).status_code == 422


def test_an_unknown_node_type_is_reported_with_the_node(client):
    pipeline_id = _create(client, 'ghost_type', node_type='contrib.no.Such')

    response = client.post(f'/pipelines/{pipeline_id}/warmup')

    assert response.status_code == 422, response.text

    answer = response.json()

    assert answer['operation'] == 'warmup'
    assert answer['node'] == 'node'
    assert answer['message'].startswith('warmup failed on node node: ')
    assert 'ModuleNotFoundError' in answer['message']

    # the pipeline is as it was, and can be deleted
    status = client.get(f'/pipelines/{pipeline_id}/status').json()

    assert status['self'] == 'pipeline_created'
    assert client.post(f'/pipelines/{pipeline_id}/delete').status_code == 200


def test_a_failed_deploy_is_reported_and_leaves_nothing(client):
    before = client.get('/pipelines').json()

    response = client.post(
        '/pipelines/deploy',
        json=_config('ghost_deploy', node_type='contrib.no.Such'),
    )

    assert response.status_code == 422, response.text
    assert response.json()['node'] == 'node'
    assert client.get('/pipelines').json() == before


def test_a_node_that_fails_to_warm_up_is_reported(client, monkeypatch):
    from juturna.cli.commands._pipeline_manager import PipelineManager

    pipeline_id = _create(client, 'failing_warmup')

    def _warmup(self):
        raise FileNotFoundError('no model at /models/x.bin')

    from juturna.components import Node

    monkeypatch.setattr(Node, 'warmup', _warmup)

    response = client.post(f'/pipelines/{pipeline_id}/warmup')

    assert response.status_code == 422
    assert response.json() == {
        'message': (
            'warmup failed on node node: '
            'FileNotFoundError: no model at /models/x.bin'
        ),
        'operation': 'warmup',
        'node': 'node',
    }
    assert PipelineManager().pipeline_status(pipeline_id)['self'] == (
        'pipeline_created'
    )


def test_a_call_the_status_does_not_allow_is_still_a_conflict(client):
    pipeline_id = _create(client, 'not_ready')

    response = client.post(f'/pipelines/{pipeline_id}/start')

    assert response.status_code == 409


# -- what a frontend needs ---------------------------------------------------


def test_status_carries_name_and_creation_time(client):
    created = client.post('/pipelines/new', json=_config('named')).json()
    pipeline_id = created['data']['pipeline_id']

    status = client.get(f'/pipelines/{pipeline_id}/status').json()

    assert status['name'] == 'named'
    assert status['created_at'] == created['data']['created_at']
    assert status['pipe_id'] == pipeline_id

    listed = client.get('/pipelines').json()['pipelines'][0][pipeline_id]

    assert listed['name'] == 'named'


def test_the_configuration_can_be_read_back(client):
    config = _config('round_trip')
    config['plugins'] = ['./plugins']
    config['pipeline']['nodes'][0]['configuration'] = {'delay': 0}

    created = client.post('/pipelines/new', json=config).json()
    pipeline_id = created['data']['pipeline_id']

    response = client.get(f'/pipelines/{pipeline_id}/config')

    assert response.status_code == 200

    stored = response.json()

    # what was sent, with the id and the folder the service gave it
    assert stored['pipeline'].pop('id') == pipeline_id
    assert stored['pipeline'].pop('folder').endswith(
        f'round_trip_{pipeline_id}'
    )
    assert stored == config

    assert client.get('/pipelines/no_such_id/config').status_code == 404


def test_the_node_catalogue_lists_the_installed_types(client):
    response = client.get('/nodes')

    assert response.status_code == 200

    nodes = {node['type']: node for node in response.json()['nodes']}

    assert list(nodes) == sorted(nodes)
    assert nodes['contrib.jt_test.nodes.Sequencer'] == {
        'type': 'contrib.jt_test.nodes.Sequencer',
        'description': '',
        'arguments': {
            'sample_length_sec': 2,
            'sample_rate': 16000,
            'sample_tone': 440,
            'audio_format': 'int16',
            'channels': 1,
            'rate': 1,
        },
    }

    # every type of the catalogue is one the builder resolves
    from juturna.components._node_builder import _builder

    for node_type in nodes:
        if node_type.startswith('contrib.jt_test.'):
            _builder._resolve_node(node_type)


def test_the_catalogue_does_not_import_the_nodes():
    import subprocess
    import sys

    code = (
        'import sys\n'
        'from juturna.cli.commands._node_catalogue import node_catalogue\n'
        'types = [n["type"] for n in node_catalogue()]\n'
        'assert "contrib.jt_test.nodes.Sequencer" in types, types\n'
        'loaded = [m for m in sys.modules if m.endswith(".sequencer")]\n'
        'assert not loaded, loaded\n'
    )
    env = {
        **os.environ,
        'PYTHONPATH': os.pathsep.join(
            [os.getcwd(), str(pathlib.Path('tests/_nodes').resolve())]
        ),
    }

    result = subprocess.run(
        [sys.executable, '-c', code], env=env, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr


def _check(report: dict, name: str) -> dict:
    return next(c for c in report['checks'] if c['name'] == name)


def test_validate_reports_without_creating(client, capsys):
    before = client.get('/pipelines').json()

    good = client.post('/pipelines/validate', json=_config('to_check'))
    bad_type = client.post(
        '/pipelines/validate',
        json=_config('to_check', node_type='contrib.no.Such'),
    )
    bad_key = client.post(
        '/pipelines/validate',
        json=_config(
            'to_check',
            nodes=[
                {
                    'name': 'node',
                    'type': _NODE_TYPE,
                    'configuration': {'no_such_key': 1},
                }
            ],
        ),
    )
    not_a_config = client.post('/pipelines/validate', json=[1, 2])

    assert good.status_code == 200
    assert good.json()['success'] is True
    assert good.json()['dag'] is not None

    assert bad_type.status_code == 200
    assert bad_type.json()['success'] is False
    assert 'contrib.no.Such' in (
        _check(bad_type.json(), 'Node types and arguments')['error']
    )

    assert bad_key.json()['success'] is True
    assert 'no_such_key' in (
        _check(bad_key.json(), 'Node types and arguments')['warnings'][0]
    )

    assert not_a_config.status_code == 200
    assert not_a_config.json()['success'] is False
    assert _check(not_a_config.json(), 'DAG properties')['skipped'] is True

    assert client.get('/pipelines').json() == before

    # the command prints its report, the service must not
    assert capsys.readouterr().out == ''


def test_files_of_a_pipeline_are_listed_and_served(client):
    from juturna.cli.commands._pipeline_manager import PipelineManager

    pipeline_id = _create(client, 'with_files')

    # the folder is made by warmup
    assert client.get(f'/pipelines/{pipeline_id}/files').json() == {
        'pipeline': pipeline_id,
        'files': [],
    }

    assert client.post(f'/pipelines/{pipeline_id}/warmup').status_code == 200

    folder = pathlib.Path(PipelineManager().pipeline_status(pipeline_id)['folder'])
    (folder / 'node' / 'out.bin').write_bytes(b'\x00\x01<b>')

    listing = client.get(f'/pipelines/{pipeline_id}/files').json()
    files = {f['path']: f for f in listing['files']}

    assert sorted(files) == ['config.json', 'node/out.bin']
    assert files['node/out.bin']['size'] == 5
    assert files['node/out.bin']['modified'] > 0

    response = client.get(f'/pipelines/{pipeline_id}/files/node/out.bin')

    assert response.status_code == 200
    assert response.content == b'\x00\x01<b>'
    assert response.headers['content-type'] == 'application/octet-stream'
    assert 'attachment' in response.headers['content-disposition']
    assert response.headers['x-content-type-options'] == 'nosniff'

    stored = client.get(f'/pipelines/{pipeline_id}/files/config.json')

    assert json.loads(stored.content)['pipeline']['name'] == 'with_files'


def test_files_outside_the_pipeline_folder_are_not_reachable(client, tmp_path):
    from juturna.cli.commands._pipeline_manager import PipelineManager
    from juturna.cli.commands.exceptions import PipelineFileNotFoundException

    manager = PipelineManager()
    pipeline_id = _create(client, 'fenced')
    other_id = _create(client, 'neighbour')

    for created in (pipeline_id, other_id):
        assert client.post(f'/pipelines/{created}/warmup').status_code == 200

    folder = pathlib.Path(manager.pipeline_status(pipeline_id)['folder'])
    other = pathlib.Path(manager.pipeline_status(other_id)['folder'])

    secret = tmp_path / 'secret.txt'
    secret.write_text('outside-content')

    (folder / 'link.txt').symlink_to(secret)
    (folder / 'linked_dir').symlink_to(tmp_path, target_is_directory=True)
    (folder / 'inner.txt').symlink_to('config.json')

    listed = [
        f['path']
        for f in client.get(f'/pipelines/{pipeline_id}/files').json()['files']
    ]

    # a link that stays in the folder is fine
    assert sorted(listed) == ['config.json', 'inner.txt']

    for path in (
        '../' + other.name + '/config.json',
        'node/../../' + other.name + '/config.json',
        str(secret),
        str(folder / 'config.json'),
        'link.txt',
        'linked_dir/secret.txt',
        'node',
        'no_such_file',
        '',
        '..\\' + other.name + '\\config.json',
    ):
        with pytest.raises(PipelineFileNotFoundException):
            manager.pipeline_file(pipeline_id, path)

    assert manager.pipeline_file(pipeline_id, 'inner.txt').name == (
        'config.json'
    )

    # through the service, with the dots encoded so the client keeps them
    for path in (
        f'%2e%2e/{other.name}/config.json',
        f'node/%2e%2e/%2e%2e/{other.name}/config.json',
        '%2e%2e%2f%2e%2e%2fpyproject.toml',
        'link.txt',
        'linked_dir/secret.txt',
        'no_such_file',
    ):
        response = client.get(f'/pipelines/{pipeline_id}/files/{path}')

        assert response.status_code == 404, path
        assert 'outside-content' not in response.text

    # not the answer of a route that does not exist: a frontend tells an
    # optional endpoint is missing from that
    missing = client.get(f'/pipelines/{pipeline_id}/files/no_such_file')

    assert missing.json() == {
        'message': f'no file no_such_file in pipeline {pipeline_id}'
    }
    assert client.get('/pipelines/no_such_id/files').status_code == 404


def test_logs_of_a_pipeline_can_be_read(client):
    from juturna.cli.commands._pipeline_manager import PipelineManager

    manager = PipelineManager()
    pipeline_id = _create(client, 'logged')
    pipeline = manager._get(pipeline_id)
    pipeline._logger.setLevel(logging.INFO)

    assert client.post(f'/pipelines/{pipeline_id}/warmup').status_code == 200

    answer = client.get(f'/pipelines/{pipeline_id}/logs').json()
    logs = answer['logs']

    assert answer['pipeline'] == pipeline_id
    assert [r['message'] for r in logs][-1] == 'pipe warmed up!'
    assert {r['level'] for r in logs} == {'INFO'}
    assert all(r['logger'].startswith('jt.logged') for r in logs)
    assert [r['ts'] for r in logs] == sorted(r['ts'] for r in logs)

    # the nodes log under the pipeline
    pipeline._nodes['node'].logger.setLevel(logging.INFO)

    try:
        raise ValueError('bad frame')
    except ValueError:
        pipeline._nodes['node'].logger.error('update failed', exc_info=True)

    newer = client.get(
        f'/pipelines/{pipeline_id}/logs', params={'since': logs[-1]['ts']}
    ).json()['logs']

    assert [r['message'] for r in newer] == ['update failed']
    assert newer[0]['logger'] == 'jt.logged.node'
    assert 'ValueError: bad frame' in newer[0]['exception']

    assert client.get('/pipelines/no_such_id/logs').status_code == 404

    # the buffer goes with the pipeline
    handlers = len(pipeline._logger.handlers)

    assert client.post(f'/pipelines/{pipeline_id}/delete').status_code == 200
    assert len(pipeline._logger.handlers) == handlers - 1
    assert pipeline_id not in manager._log_buffers


def test_the_log_buffer_keeps_the_last_records():
    from juturna.cli.commands._pipeline_manager import _LogBuffer

    buffer = _LogBuffer(size=3)
    logger = logging.Logger('buffered')
    logger.addHandler(buffer)

    for i in range(5):
        logger.warning('record %d', i)

    assert [r['message'] for r in buffer.records()] == [
        'record 2',
        'record 3',
        'record 4',
    ]


def test_status_polls_are_not_logged_at_info(client, caplog):
    pipeline_id = _create(client, 'polled')

    with caplog.at_level(logging.INFO, logger='jt.manager'):
        logging.getLogger('jt.manager').propagate = True

        try:
            client.get(f'/pipelines/{pipeline_id}/status')
        finally:
            logging.getLogger('jt.manager').propagate = True

    assert not [r for r in caplog.records if r.name == 'jt.manager']


def test_health_says_what_failed_last(wait_for_condition):
    from juturna.components import Message
    from juturna.components import Node

    class Failing(Node):
        def update(self, message, **kwargs):
            raise ValueError(f'bad frame {message.version}')

    node = Failing(node_name='failing', pipe_name='test_pipe')

    assert node.health['last_failure'] is None

    node.start()
    node.put(Message(creator='test', version=1))
    node.put(Message(creator='test', version=2))

    try:
        assert wait_for_condition(
            lambda: node.health['update_failures'] == 2, timeout=5
        )
        assert node.health['last_failure'] == 'ValueError: bad frame 2'
    finally:
        node.stop()


def test_the_manager_is_one_instance_also_when_empty(client):
    from juturna.cli.commands._pipeline_manager import PipelineManager

    manager = PipelineManager()

    assert len(manager) == 0
    assert PipelineManager() is manager
