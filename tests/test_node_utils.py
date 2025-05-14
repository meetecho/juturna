import pathlib
import shutil

import pytest

from juturna.utils import node_utils


def test_node_stub(tmp_path):
    node_name = 'test_node'
    node_type = 'test_type'
    temp_dir = tmp_path / 'test_node_stub'

    node_utils.node_stub(node_name, node_type, destination=temp_dir)

    assert pathlib.Path(temp_dir, node_type,
                         f'_{node_name}').exists()

    assert pathlib.Path(temp_dir, node_type,
                        f'_{node_name}', f'{node_name}.py').exists()

    assert pathlib.Path(temp_dir, node_type,
                        f'_{node_name}', 'config.toml').exists()

    assert pathlib.Path(temp_dir, node_type,
                         f'_{node_name}', 'README.md').exists()
    
    assert pathlib.Path(temp_dir, node_type,
                        f'_{node_name}', 'requirements.txt').exists()


def test_node_stub_existing_node(tmp_path):
    node_name = 'test_node'
    node_type = 'test_type'
    temp_dir = tmp_path / 'test_node_stub'

    pathlib.Path(temp_dir, node_type,
                 f'_{node_name}').mkdir(parents=True)
    
    with pytest.warns(UserWarning):
        node_utils.node_stub(node_name, node_type, destination=temp_dir)