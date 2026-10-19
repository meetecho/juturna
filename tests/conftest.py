import importlib.util
import pathlib
import shutil
import itertools
import time

import pytest

import juturna as jt
from juturna.components import Message, Node

class SlowNode(Node):
    """Nodo che simula un carico di lavoro per testare il draining."""
    def update(self, message):
        # Simula un'elaborazione che richiede tempo per testare il join()
        time.sleep(0.05)

test_pipeline_folder = './tests/running_pipelines'

def pytest_addoption(parser):
    parser.addoption(
        '--keep-data',
        action='store_true',
        default=False,
        help='Do not delete the folder created for test pipelines'
    )


@pytest.fixture
def wait_for_condition():
    def _wait(condition_fn, timeout=10.0, interval=0.1):
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if condition_fn():
                return True

            time.sleep(interval)

        return False

    return _wait

SERVICE_TOKEN = 'test-service-token'


@pytest.fixture
def service_app():
    # the service needs the httpwrapper extra, which CI does not install, and
    # the starlette test client needs httpx2 (or httpx)
    pytest.importorskip('fastapi')

    if not any(importlib.util.find_spec(m) for m in ('httpx2', 'httpx')):
        pytest.skip('the starlette test client needs httpx2')

    from juturna.cli.commands._juturna_service import app
    from juturna.components._pipeline_manager import PipelineManager

    PipelineManager.set_base_folder(test_pipeline_folder)
    app.state.token = SERVICE_TOKEN
    app.state.auth = True

    yield app

    app.state.token = None
    app.state.auth = True
    PipelineManager.set_allowed_env_vars(list())


@pytest.fixture
def service_client(service_app):
    from fastapi.testclient import TestClient

    return TestClient(
        service_app, headers={'Authorization': f'Bearer {SERVICE_TOKEN}'}
    )


@pytest.fixture(scope='session')
def test_config():
    config = {
        'test_pipeline_folder': test_pipeline_folder
    }

    yield config

    ...


@pytest.fixture(autouse=True)
def reset_message_counter():
    jt.components.Message._id_gen = itertools.count()

    yield

    ...

@pytest.fixture(autouse=True, scope='session')
def prepare_pipe_folder(request):
    keep = request.config.getoption('--keep-data')

    pathlib.Path(test_pipeline_folder).mkdir(exist_ok=True, parents=True)

    yield

    if not keep:
        try:
            shutil.rmtree(test_pipeline_folder)
        except Exception:
            ...
