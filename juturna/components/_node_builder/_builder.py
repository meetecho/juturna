from juturna.components._node_builder import _builder_internal
from juturna.components._node_builder import _builder_external
from juturna.components._node_builder import _utils


_EXTERNAL_PLUGIN_MIN_VER = 3
_INTERNAL_PLUGIN_MAX_VER = 2


def _get_node(
    node: dict, pipe_name: str, build_version: int, plugin_dirs: list = None
):
    if _utils._semver(build_version)[0] >= _EXTERNAL_PLUGIN_MIN_VER:
        return _builder_external.build_node(node, pipe_name=pipe_name)

    if _utils._semver(build_version)[0] <= _INTERNAL_PLUGIN_MAX_VER:
        return _builder_internal.build_component(
            node, plugin_dirs=plugin_dirs, pipe_name=pipe_name
        )
