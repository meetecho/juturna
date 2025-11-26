import pathlib
import typing
import traceback

from juturna.components import _mapper as mapper

from juturna.utils.log_utils import jt_logger
from juturna.components._synchronisers import _SYNCHRONISERS


_logger = jt_logger('builder')


def build_component(node: dict, plugin_dirs: list, pipe_name: str):
    node_name = node['name']
    node_type = node['type']
    node_mark = node['mark']
    node_sync = node.get('sync')
    node_remote_config = node['configuration']

    base_node_explore = component_lookup_args(
        component_type=node_type,
        component_mark=node_mark,
        plugin_dirs=plugin_dirs,
    )

    _node_module, _node_local_config, _exceptions = fetch_node(
        base_node_explore
    )

    if _node_module is None:
        _logger.info(f'node {node_name} cannot be imported, possible causes:')

        for exc in _exceptions:
            _log_import_exception(exc)

        raise ModuleNotFoundError(f'node module not found: {node_name}')

    operational_config = _update_local_with_remote(
        _node_local_config['arguments'], node_remote_config
    )

    synchroniser = _SYNCHRONISERS.get(node_sync)
    concrete_node = _node_module(
        **operational_config,
        **{
            'node_name': node_name,
            'pipe_name': pipe_name,
            'synchroniser': synchroniser,
        },
    )

    concrete_node.configure()

    return concrete_node


def fetch_node(fetch_args: list) -> tuple:
    return _fetch_component(fetch_args, mapper.node)


def _fetch_component(fetch_args: list, fetch_fun: typing.Callable) -> tuple:
    _component, _config, _exceptions = None, None, list()

    for args in fetch_args:
        try:
            _component, _config = fetch_fun(**args)
        except Exception as e:
            _exceptions.append(e)

    return _component, _config, _exceptions


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


def _log_import_exception(exception):
    error_type = type(exception).__name__
    error_msg = str(exception)

    if isinstance(exception, SyntaxError):
        filename = exception.filename
        line_number = exception.lineno
        code_context = (
            exception.text.strip() if exception.text else 'Context unavailable'
        )
    else:
        tb_summary = traceback.extract_tb(exception.__traceback__)

        if not tb_summary:
            _logger.error(f'{error_type}: {error_msg} (No traceback available)')

            return

        last_frame = tb_summary[-1]

        filename = last_frame.filename
        line_number = last_frame.lineno
        code_context = (
            last_frame.line.strip()
            if last_frame.line
            else 'Context unavailable'
        )

    _logger.error(
        f'{error_type} in {filename}, line {line_number}: '
        f'{code_context} - {error_msg}'
    )
