from juturna.components._node_builder import _builder_internal
from juturna.components._node_builder import _builder_external


def _get_node(node: dict, pipe_name: str, plugin_dirs: list = None):
    """
    Build a concrete node
    The current building system instantiates both local and external nodes. The
    key differentiating them is mark, only available for local nodes. Hence, if
    the passed node has the mark attribute, it will be treated as a local node
    (and therefore, a plugin directory will be required), otherwise the node
    will be treated as external.
    """
    if node.get('mark'):
        print('INTERNAL BUILDER')
        return _builder_internal.build_component(
            node, plugin_dirs=plugin_dirs, pipe_name=pipe_name
        )

    print('EXTERNAL BUILDER')
    return _builder_external.build_node(node, pipe_name=pipe_name)
