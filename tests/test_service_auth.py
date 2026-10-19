import argparse

import pytest

from tests.conftest import SERVICE_TOKEN


test_pipeline_folder = './tests/running_pipelines'


def _config(name: str, configuration: dict | None = None) -> dict:
    return {
        'version': '3.0.0',
        'pipeline': {
            'name': name,
            'id': name,
            'folder': f'{test_pipeline_folder}/{name}',
            'nodes': [
                {
                    'name': 'node',
                    'type': 'contrib.jt_test.nodes.PassthroughIdentity',
                    'configuration': configuration or {},
                }
            ],
            'links': [],
        },
    }


def _routes(app) -> list[tuple[str, str]]:
    from fastapi.routing import APIRoute

    return [
        (method, route.path.replace('{pipeline_id}', 'no_such_id'))
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    ]


@pytest.fixture
def anonymous_client(service_app):
    from fastapi.testclient import TestClient

    return TestClient(service_app)


def test_every_route_requires_the_token(service_app, anonymous_client):
    routes = _routes(service_app)

    assert len(routes) == 10

    for method, path in routes:
        response = anonymous_client.request(method, path)

        assert response.status_code == 401, (method, path)
        assert response.headers['www-authenticate'] == 'Bearer'


@pytest.mark.parametrize(
    'authorization',
    [
        'Bearer wrong-token',
        f'Bearer {SERVICE_TOKEN}x',
        f'Basic {SERVICE_TOKEN}',
        SERVICE_TOKEN,
        'Bearer ',
    ],
)
def test_wrong_credentials_are_rejected(anonymous_client, authorization):
    response = anonymous_client.get(
        '/pipelines', headers={'Authorization': authorization}
    )

    assert response.status_code == 401


def test_the_token_grants_access(service_client):
    assert service_client.get('/pipelines').status_code == 200
    assert service_client.get('/configuration').status_code == 200


def test_cross_site_simple_post_is_rejected(anonymous_client):
    # what a foreign page can send without a CORS preflight
    response = anonymous_client.post(
        '/pipelines/no_such_id/delete?wipe=true',
        content='x',
        headers={
            'Content-Type': 'text/plain',
            'Origin': 'https://evil.example',
        },
    )

    assert response.status_code == 401


def test_requests_fail_closed_without_a_configured_token(
    service_app, anonymous_client, monkeypatch
):
    from juturna.cli.commands._juturna_service import TOKEN_ENV_VAR

    service_app.state.token = None
    monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)

    response = anonymous_client.get(
        '/pipelines', headers={'Authorization': 'Bearer anything'}
    )

    assert response.status_code == 503


def test_token_is_read_from_the_environment_when_not_set_by_run(
    service_app, anonymous_client, monkeypatch
):
    from juturna.cli.commands._juturna_service import TOKEN_ENV_VAR

    # e.g. the app served with "fastapi run" instead of "juturna serve"
    service_app.state.token = None
    monkeypatch.setenv(TOKEN_ENV_VAR, 'env-token')

    ok = anonymous_client.get(
        '/pipelines', headers={'Authorization': 'Bearer env-token'}
    )
    ko = anonymous_client.get(
        '/pipelines', headers={'Authorization': f'Bearer {SERVICE_TOKEN}'}
    )

    assert ok.status_code == 200
    assert ko.status_code == 401


def test_dev_cors_does_not_reflect_the_origin_with_credentials():
    pytest.importorskip('fastapi')

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from juturna.cli.commands._juturna_service import enable_cross_origins

    dev_app = FastAPI()
    enable_cross_origins(dev_app)
    dev_app.get('/ping')(lambda: {'pong': True})

    client = TestClient(dev_app)
    response = client.get('/ping', headers={'Origin': 'https://evil.example'})
    preflight = client.options(
        '/ping',
        headers={
            'Origin': 'https://evil.example',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'authorization',
        },
    )

    assert response.headers['access-control-allow-origin'] == '*'
    assert 'access-control-allow-credentials' not in response.headers
    assert preflight.status_code == 200
    assert 'access-control-allow-credentials' not in preflight.headers


@pytest.mark.parametrize('endpoint', ['new', 'deploy'])
def test_service_rejects_env_vars_not_allowed(service_client, endpoint):
    from juturna.components._pipeline_manager import PipelineManager

    before = len(PipelineManager())
    response = service_client.post(
        f'/pipelines/{endpoint}',
        json=_config('env_pipe', {'secret': '$JT_ENV_SERVICE_SECRET'}),
    )

    assert response.status_code == 403
    assert 'SERVICE_SECRET' in response.json()['message']
    assert len(PipelineManager()) == before


def test_service_accepts_allowed_env_vars(service_client):
    from juturna.components._pipeline_manager import PipelineManager

    PipelineManager.set_allowed_env_vars(['MODEL_DIR'])

    response = service_client.post(
        '/pipelines/new',
        json=_config('env_allowed_pipe', {'model': '$JT_ENV_MODEL_DIR'}),
    )

    assert response.status_code == 200

    pipe_id = response.json()['data']['pipeline_id']
    service_client.post(f'/pipelines/{pipe_id}/delete?wipe=true')


def test_manager_rejects_env_vars_for_direct_callers(service_app):
    from juturna.cli.commands.exceptions import EnvVarNotAllowedException
    from juturna.cli.commands.models.api import PipelineConfig
    from juturna.components._pipeline_manager import PipelineManager

    config = PipelineConfig(**_config('env_pipe', {'k': '$JT_ENV_HOME'}))

    with pytest.raises(EnvVarNotAllowedException) as error:
        PipelineManager().create_pipeline(config)

    assert (error.value.var_name, error.value.node_name) == ('HOME', 'node')


@pytest.mark.parametrize(
    'host, loopback',
    [
        ('127.0.0.1', True),
        ('127.0.0.2', True),
        ('::1', True),
        ('localhost', True),
        ('0.0.0.0', False),
        ('::', False),
        ('192.168.1.10', False),
        ('example.com', False),
    ],
)
def test_is_loopback(host, loopback):
    pytest.importorskip('fastapi')

    from juturna.cli.commands._juturna_service import _is_loopback

    assert _is_loopback(host) is loopback


def _serve_args(*argv) -> argparse.Namespace:
    from juturna.cli.commands import serve

    parser = argparse.ArgumentParser()
    serve.setup_parser(parser.add_subparsers())

    return parser.parse_args(['serve', *argv])


def test_serve_binds_localhost_by_default():
    pytest.importorskip('fastapi')

    args = _serve_args('-p', '1234', '-f', 'folder')

    assert args.host == '127.0.0.1'
    assert args.allow_env == []
    assert args.auth is True


def test_serve_no_auth_turns_the_token_off():
    pytest.importorskip('fastapi')

    args = _serve_args('-p', '1234', '-f', 'folder', '--no-auth')

    assert args.auth is False


def test_serve_allow_env_is_repeatable():
    pytest.importorskip('fastapi')

    args = _serve_args('-p', '1', '-f', 'f', '-e', 'A', '--allow-env', 'B')

    assert args.allow_env == ['A', 'B']


def _run(monkeypatch, tmp_path, **kwargs):
    from juturna.cli.commands import _juturna_service

    monkeypatch.setattr(_juturna_service.uvicorn, 'run', lambda *a, **k: None)

    _juturna_service.run(
        kwargs.pop('host', '127.0.0.1'),
        1234,
        str(tmp_path / 'pipes'),
        None,
        False,
        **kwargs,
    )

    return _juturna_service.app


def test_run_generates_a_token_and_prints_it_without_logging_it(
    service_app, monkeypatch, tmp_path, capsys, caplog
):
    from juturna.cli.commands._juturna_service import TOKEN_ENV_VAR

    monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)

    with caplog.at_level('DEBUG'):
        app = _run(monkeypatch, tmp_path)

    token = app.state.token

    assert len(token) >= 32
    assert token in capsys.readouterr().err
    assert token not in caplog.text


def test_run_uses_the_token_from_the_environment(
    service_app, monkeypatch, tmp_path, capsys
):
    from juturna.cli.commands._juturna_service import TOKEN_ENV_VAR

    monkeypatch.setenv(TOKEN_ENV_VAR, 'operator-token')
    app = _run(monkeypatch, tmp_path)

    assert app.state.token == 'operator-token'
    assert 'operator-token' not in capsys.readouterr().err


def test_run_sets_the_allowed_env_vars(service_app, monkeypatch, tmp_path):
    from juturna.components._pipeline_manager import PipelineManager

    _run(monkeypatch, tmp_path, allow_env=['MODEL_DIR'])

    assert PipelineManager._allowed_env_vars == frozenset({'MODEL_DIR'})


def test_run_warns_when_bound_to_the_network(
    service_app, monkeypatch, tmp_path, caplog
):
    with caplog.at_level('WARNING', logger='jt.service'):
        _run(monkeypatch, tmp_path, host='0.0.0.0')

    assert 'TLS' in caplog.text


def test_run_without_auth_accepts_requests_without_a_token(
    service_app, anonymous_client, monkeypatch, tmp_path, capsys, caplog
):
    from juturna.cli.commands._juturna_service import TOKEN_ENV_VAR

    monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)

    with caplog.at_level('WARNING', logger='jt.service'):
        app = _run(monkeypatch, tmp_path, auth=False)

    assert app.state.token is None
    assert 'generated service token' not in capsys.readouterr().err
    assert 'authentication disabled' in caplog.text

    for method, path in _routes(service_app):
        response = anonymous_client.request(method, path)

        assert response.status_code not in (401, 503), (method, path)


def test_run_without_auth_ignores_the_token_from_the_environment(
    service_app, anonymous_client, monkeypatch, tmp_path, caplog
):
    from juturna.cli.commands._juturna_service import TOKEN_ENV_VAR

    monkeypatch.setenv(TOKEN_ENV_VAR, 'operator-token')

    with caplog.at_level('WARNING', logger='jt.service'):
        app = _run(monkeypatch, tmp_path, auth=False)

    assert app.state.token is None
    assert f'{TOKEN_ENV_VAR} is set but ignored' in caplog.text
    assert anonymous_client.get('/pipelines').status_code == 200
