import pathlib

from juturna.components._node_builder import _builder
from juturna.components._node import Node
from juturna.names import ComponentStatus

from juturna.meta import JUTURNA_EXTERNAL_PLUGIN_MIN_VER
from juturna.meta import JUTURNA_INTERNAL_PLUGIN_MAX_VER

REMOTE_PIPE_FOLDER = 'remote_pipes'
REMOTE_PIPE_ID = 'remote_pipe'


def _standalone_builder(
    name: str,
    node_mark: str,
    node_type: str,
    context_runtime_path: str,
    config: dict = None,
    plugin_dir: str = '',
) -> tuple[Node | None, dict]:
    """
    Deploys a node remotely by importing its module and returning its class
    along with its configuration.
    This function is responsible for deploying a node remotely by dynamically
    importing its module based on the provided node name. It constructs the
    module path, imports the module, and retrieves the node class and its
    configuration.

    Parameters
    ----------
    name : str
        The name of the node to be deployed.
    node_mark : str
        The mark of the node to be deployed.
    node_type : str
        Type of the node to be deployed.
    context_runtime_path : str
        The runtime path for the context.
    plugin_dir : str
        The directory where plugins are located.
    config : dict
        The configuration dictionary for the node.

    Returns
    -------
    Tuple[Node, pathlib.Path]
        A tuple containing the node instance and its runtime folder path.

    """
    node = {
        'name': name,
        'type': 'proc',
        'mark': node_mark,
        'configuration': config,
    }

    build_version = JUTURNA_INTERNAL_PLUGIN_MAX_VER

    if node_type:
        del node['mark']

        node['type'] = node_type
        build_version = JUTURNA_EXTERNAL_PLUGIN_MIN_VER

    node_runtime_folder = pathlib.Path(REMOTE_PIPE_FOLDER, context_runtime_path)
    node_runtime_folder.mkdir(exist_ok=True, parents=True)

    plugin_dirs = [plugin_dir] if plugin_dir else None

    _node: Node = _builder._get_node(
        node,
        pipe_name=context_runtime_path,
        build_version=str(build_version),
        plugin_dirs=plugin_dirs,
    )

    _node.pipe_id = context_runtime_path
    _node.pipe_path = node_runtime_folder
    _node.status = ComponentStatus.NEW

    _node.warmup()
    _node.status = ComponentStatus.CONFIGURED

    _node.start()
    _node.status = ComponentStatus.RUNNING

    return _node, node_runtime_folder
