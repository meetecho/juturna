import pathlib
import typing

from juturna.components import _mapper as mapper

from juturna.utils.log_utils import jt_logger
from juturna.components._synchronisation_policy import _POLICIES


_logger = jt_logger()


def build_component(node: dict, plugin_dirs: list, pipe_name: str):
    node_name = node['name']
    node_type = node['type']
    node_mark = node['mark']
    node_policy = node.get('policy')
    node_remote_config = node['configuration']

    # plugin_dirs.insert(0, jt.meta.JUTURNA_CACHE_DIR)

    # nodes should be built starting from the default built-in folder, then all
    # the plugin folders specified in the configuration file should be tested
    # TODO: refactor this monstrosity
    base_node_explore = component_lookup_args(
        component_type=node_type,
        component_mark=node_mark,
        plugin_dirs=plugin_dirs,
    )
    _node_module, _node_local_config = fetch_node(base_node_explore)

    if _node_module is None:
        raise ModuleNotFoundError(f'node module not found: {node_name}')

    operational_config = _update_local_with_remote(
        _node_local_config['arguments'], node_remote_config
    )

    # del node_policy['name']
    # policy = _POLICIES[node_policy](node_policy) if node_policy else None
    policy = _POLICIES[node_policy]() if node_policy else None

    concrete_node = _node_module(
        **operational_config,
        **{
            'node_type': node_type,
            'node_name': node_name,
            'pipe_name': pipe_name,
            'policy': policy
        },
    )
    concrete_node.configure()

    return concrete_node


def fetch_node(fetch_args: list) -> tuple:
    return _fetch_component(fetch_args, mapper.node)


def _fetch_component(fetch_args: list, fetch_fun: typing.Callable) -> tuple:
    _component, _config = None, None

    for args in fetch_args:
        try:
            _component, _config = fetch_fun(**args)
        except ModuleNotFoundError as _:
            ...
        except Exception as e:
            _logger.warning(e)

    return _component, _config


def component_lookup_args(
    component_type: str,
    component_mark: str,
    plugin_dirs: list | None = None,
):
    plugin_dirs = plugin_dirs or list()
    plugin_dirs = [
        '.'.join(pathlib.Path(p, 'nodes').parts) for p in plugin_dirs
    ]

    def_args = {'node_type': component_type, 'node_name': component_mark}
    def_args = [def_args] + [
        {'import_prefix': p, **def_args} for p in plugin_dirs
    ]

    return def_args


def _update_local_with_remote(local: dict, remote: dict) -> dict:
    merged_config = {k: remote.get(k, v) for k, v in local.items()}

    return merged_config