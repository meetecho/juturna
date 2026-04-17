import pathlib
import shutil
import itertools
import time

import pytest

import juturna as jt
from juturna.components import Message, Node
from juturna.payloads import ControlPayload, ControlSignal

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
