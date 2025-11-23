import pathlib
import typing
import os

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
        _node_local_config.get('arguments', {}), node_remote_config, node_name=node_name
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


def _cast_value_to_type(value: str, default_value: typing.Any) -> typing.Any:
    """
    Cast a string value to the type of the default value.
    
    Parameters
    ----------
    value : str
        The string value to cast.
    default_value : Any
        The default value whose type will be used for casting.
    
    Returns
    -------
    Any
        The value cast to the appropriate type.
    """
    if isinstance(default_value, bool):
        return value.lower() in ('true', 'yes', '1', 'y', 'on')
    elif isinstance(default_value, int):
        try:
            return int(value)
        except ValueError:
            raise ValueError(f'Cannot cast "{value}" to integer')
    elif isinstance(default_value, float):
        try:
            return float(value)
        except ValueError:
            raise ValueError(f'Cannot cast "{value}" to float')
    else:
        return value


def _resolve_env_var_value(value: str, env_var_name: str, config_key: str, 
                           default_value: typing.Any, node_name: str) -> typing.Any:
    """
    Resolve an environment variable value and cast it to the appropriate type.
    
    Parameters
    ----------
    value : str
        The original value from config (should start with $JT_ENV_).
    env_var_name : str
        The environment variable name (after stripping $JT_ENV_ prefix).
    config_key : str
        The configuration key name.
    default_value : Any
        The default value from TOML config (used for type inference).
    node_name : str
        The name of the node being processed.
    
    Returns
    -------
    Any
        The resolved and type-cast value from environment.
    
    Raises
    ------
    ValueError
        If the environment variable is not set.
    """
    env_value = os.environ.get(env_var_name)
    if env_value is None:
        error_msg = (
            f'Environment variable "{env_var_name}" is not set in node "{node_name}" '
            f'for config key "{config_key}". Referenced in configuration but not found in environment.'
        )
        _logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Cast to type of default value
    try:
        cast_value = _cast_value_to_type(env_value, default_value)
    except ValueError as e:
        error_msg = (
            f'Type casting error in node "{node_name}" for config key "{config_key}": {e}. '
            f'Expected type based on default value: {type(default_value).__name__}'
        )
        _logger.error(error_msg)
        raise ValueError(error_msg) from e
    
    # Log the resolution (mask sensitive values for security)
    masked_value = _mask_sensitive_value(env_var_name, env_value)
    _logger.info(
        f'resolved environment variable ${env_var_name} -> {masked_value} '
        f'(config key "{config_key}" in node "{node_name}")'
    )
    
    return cast_value


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


def _update_local_with_remote(local: dict, remote: dict, node_name: str = '') -> dict:
    """
    Merge local (TOML defaults) and remote (pipeline config) configurations.
    
    If a remote value starts with "$JT_ENV_", it is resolved from environment
    and cast to the type of the local default value.
    
    Parameters
    ----------
    local : dict
        Local configuration from TOML file (defaults with types).
    remote : dict
        Remote configuration from pipeline config file.
    node_name : str, optional
        Name of the node being processed, used for logging context.
    
    Returns
    -------
    dict
        Merged configuration with env vars resolved and type-cast.
    """
    ENV_VAR_PREFIX = '$JT_ENV_'
    merged_config = {}
    
    for key, default_value in local.items():
        if key in remote:
            remote_value = remote[key]
            
            # Check if value starts with $JT_ENV_ prefix
            if isinstance(remote_value, str) and remote_value.startswith(ENV_VAR_PREFIX):
                # Strip prefix to get environment variable name
                env_var_name = remote_value[len(ENV_VAR_PREFIX):]
                
                # Resolve from environment and cast to type
                resolved_value = _resolve_env_var_value(
                    remote_value, env_var_name, key, default_value, node_name
                )
                merged_config[key] = resolved_value
            else:
                # Use remote value as-is (normal assignment)
                merged_config[key] = remote_value
        else:
            # Use local default value
            merged_config[key] = default_value
    
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
