import pathlib

from juturna.components import _component_builder
from juturna.components._node import Node
from juturna.names import ComponentStatus

REMOTE_PIPE_FOLDER = 'remote_pipes'
REMOTE_PIPE_ID = 'remote_pipe'


def _standalone_builder(
    name: str,
    node_mark: str,
    plugins_dir: str,
    context_runtime_path: str,
    config: dict = None,
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
    plugins_dir : str
        The directory where plugins are located.
    context_runtime_path : str
        The runtime path for the context.
    config : dict
        The configuration dictionary for the node.

    Returns
    -------
    Tuple[Node, pathlib.Path]
        A tuple containing the node instance and its runtime folder path.

    """
    # construct a node dictionary to pass to the component builder
    node = {
        'name': name,
        'type': 'proc',
        'mark': node_mark,
        'configuration': config,
    }
    node_runtime_folder = pathlib.Path(REMOTE_PIPE_FOLDER, context_runtime_path)
    node_runtime_folder.mkdir(exist_ok=True, parents=True)

    # build the node
    _node: Node = _component_builder.build_component(
        node,
        plugin_dirs=[plugins_dir],
        pipe_name=context_runtime_path,
    )

    _node.pipe_id = context_runtime_path
    _node.pipe_path = node_runtime_folder
    _node.status = ComponentStatus.NEW

    # warmup the node
    _node.warmup()
    _node.status = ComponentStatus.CONFIGURED

    # start the node
    _node.start()
    _node.status = ComponentStatus.RUNNING

    return _node, node_runtime_folder
