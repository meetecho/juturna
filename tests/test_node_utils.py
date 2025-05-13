import tempfile
import pathlib

import pytest

from juturna.utils import node_utils


def test_node_stub(tmp_path):
    node_name = 'test_node'
    node_type = 'test_type'
    temp_dir = tmp_path / 'test_node_stub'

    # Call the function to create a node stub
    node_utils.node_stub(node_name, node_type, destination=temp_dir)

    # Check if the directory was created
    assert pathlib.Path(temp_dir, 'nodes', node_type,
                         f'_{node_name}').exists()

    # Check if the README file was created
    assert pathlib.Path(temp_dir, 'nodes', node_type,
                         f'_{node_name}', 'README.md').exists()


def test_node_stub_existing_node(tmp_path):
    node_name = 'test_node'
    node_type = 'test_type'
    temp_dir = tmp_path / 'test_node_stub'

    # Create the directory first
    pathlib.Path(temp_dir, 'nodes', node_type,
                 f'_{node_name}').mkdir(parents=True)

    # Call the function to create a node stub
    node_utils.node_stub(node_name, node_type, destination=temp_dir)

    # Check if the warning was raised
    with pytest.warns(UserWarning):
        node_utils.node_stub(node_name, node_type, destination=temp_dir)