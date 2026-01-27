import pathlib
import shutil

import pytest


test_pipeline_folder = './tests/running_pipelines'


def pytest_addoption(parser):
    parser.addoption(
        '--keep-data',
        action='store_true',
        default=False,
        help='Do not delete the folder created for test pipelines'
    )


@pytest.fixture(scope='session')
def test_config():
    config = {
        'test_pipeline_folder': test_pipeline_folder
    }

    yield config

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
