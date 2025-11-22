import pathlib
import typing
import os
import re

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

    # Resolve environment variable references in the remote configuration
    _logger.info(f'resolving environment variables for node "{node_name}"')
    node_remote_config = _resolve_env_vars(node_remote_config, node_name=node_name)

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


def _resolve_env_vars(value: typing.Any, node_name: str = '', config_key: str = '') -> typing.Any:
    """
    Recursively resolve environment variable references in configuration values.
    
    Environment variables are referenced using the syntax ${ENV_VAR_NAME}.
    This function traverses dictionaries and lists to resolve all env var references.
    
    Parameters
    ----------
    value : Any
        The configuration value to process. Can be a string, dict, list, or other type.
    node_name : str, optional
        The name of the node being processed, used for logging context.
    config_key : str, optional
        The configuration key being processed, used for logging context.
    
    Returns
    -------
    Any
        The value with environment variables resolved. If a string contains ${VAR_NAME},
        it will be replaced with the value of the environment variable.
    
    Raises
    ------
    ValueError
        If an environment variable reference is found but the variable is not set.
    
    Examples
    --------
    >>> _resolve_env_vars("${API_KEY}")
    "actual_api_key_value"
    
    >>> _resolve_env_vars({"token": "${SECRET_TOKEN}", "host": "localhost"})
    {"token": "actual_secret_value", "host": "localhost"}
    
    >>> _resolve_env_vars(["${VAR1}", "${VAR2}"])
    ["value1", "value2"]
    """
    if isinstance(value, str):
        # Pattern to match ${ENV_VAR_NAME}
        env_var_pattern = r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}'
        
        def replace_env_var(match):
            env_var_name = match.group(1)
            env_value = os.environ.get(env_var_name)
            if env_value is None:
                context = f' in node "{node_name}"' if node_name else ''
                key_context = f' for config key "{config_key}"' if config_key else ''
                error_msg = (
                    f'Environment variable "{env_var_name}" is not set{context}{key_context}. '
                    f'Referenced in configuration but not found in environment.'
                )
                _logger.error(error_msg)
                raise ValueError(error_msg)
            
            context_info = f'node "{node_name}"' if node_name else 'configuration'
            key_info = f'config key "{config_key}"' if config_key else 'value'
            masked_value = _mask_sensitive_value(env_var_name, env_value)
            _logger.info(
                f'resolved environment variable ${env_var_name} -> {masked_value} '
                f'({key_info} in {context_info})'
            )
            return env_value
        
        # Replace all ${VAR_NAME} patterns with actual env var values
        resolved = re.sub(env_var_pattern, replace_env_var, value)
        return resolved
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v, node_name=node_name, config_key=k) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item, node_name=node_name, config_key=config_key) for item in value]
    else:
        return value


def _mask_sensitive_value(var_name: str, value: str) -> str:
    """
    Mask sensitive values in logs for security.
    
    Masks values that appear to be secret keys, tokens, or passwords.
    Shows first 4 and last 4 characters with asterisks in between.
    """
    sensitive_keywords = ['key', 'token', 'secret', 'password', 'passwd', 'pwd', 'auth', 'credential']
    
    var_lower = var_name.lower()
    is_sensitive = any(keyword in var_lower for keyword in sensitive_keywords)
    
    if is_sensitive and len(value) > 8:
        return f'{value[:4]}****{value[-4:]}'
    elif is_sensitive:
        return '****'
    else:
        return value


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
