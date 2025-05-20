import pathlib
import typing

import juturna as jt

from juturna.components import _mapper as mapper
from juturna.components._buffer import Buffer


def build_component(node: dict, plugin_dirs: list):
    node_name = node['name']
    node_type = node['type']
    node_mark = node['mark']
    node_remote_config = node['configuration']

    if node_remote_config.get('buffer', None) is None:
        buffer_remote_config = { 'type': 'buffer' }
    else:
        buffer_remote_config = node_remote_config['buffer']
        del node_remote_config['buffer']

    plugin_dirs.insert(0, jt.meta.JUTURNA_CACHE_DIR)

    # nodes should be built starting from the default built-in folder, then all
    # the plugin folders specified in the configuration file should be tested
    # TODO: refactor this monstrosity
    base_node_explore = component_lookup_args(
        component_type=node_type,
        component_mark=node_mark,
        plugin_dirs=plugin_dirs)
    _node_module, _node_local_config = fetch_node(base_node_explore)

    if _node_module is None:
        raise ModuleNotFoundError(f'node module not found: {node_name}')

    operational_config = _update_local_with_remote(
        _node_local_config['arguments'], node_remote_config)

    concrete_node = _node_module(**operational_config)
    concrete_node.name = node_name
    concrete_node.configure()
    concrete_buffer = _build_buf(buffer_remote_config)

    return concrete_node, concrete_buffer


def _build_buf(buffer_remote_config: dict) -> Buffer | None:
    if not buffer_remote_config:
        return None

    buffer_type = buffer_remote_config['type']
    buffer_name = buffer_remote_config.get('name', '')

    if buffer_type == 'buffer':
        buffer = Buffer()
        buffer.name = buffer_name

        return buffer

    base_buf_explore = component_lookup_args(buffer_type)
    _buffer_module, _buffer_local_config = fetch_buffer(base_buf_explore)

    if _buffer_module is None:
        raise ModuleNotFoundError()

    buffer_operational_config = _update_local_with_remote(
        _buffer_local_config, buffer_remote_config)

    concrete_buffer = _buffer_module(**buffer_operational_config)
    concrete_buffer.name = buffer_name

    return concrete_buffer


def fetch_node(fetch_args: list) -> tuple:
    return _fetch_component(fetch_args, mapper.node)


def fetch_buffer(fetch_args: list) -> tuple:
    return _fetch_component(fetch_args, mapper.buffer)


def _fetch_component(fetch_args: list, fetch_fun: typing.Callable) -> tuple:
    _component, _config = None, None

    for args in fetch_args:
        try:
            _component, _config = fetch_fun(**args)
        except ModuleNotFoundError as e:
            ...

    return _component, _config


def component_lookup_args(
        component_type: str,
        component_mark: str | None = None,
        plugin_dirs: list | None = None):
    sub = 'nodes' if component_mark else 'buffers'
    plugin_dirs = plugin_dirs or list()
    plugin_dirs = ['.'.join(pathlib.Path(p, sub).parts) for p in plugin_dirs]

    def_args = {'node_type': component_type, 'node_name': component_mark} if \
        component_mark else {'buf_type': component_type}
    def_args = [def_args] + \
        [{'import_prefix': p, **def_args} for p in plugin_dirs]

    return def_args


def _update_local_with_remote(local: dict, remote: dict) -> dict:
    merged_config = dict()

    for k, v in local.items():
        merged_config[k] = remote[k] if k in remote.keys() else v

    return merged_config
