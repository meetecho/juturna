import fnmatch
import importlib
import os

from collections.abc import Iterable
from collections.abc import Mapping

from juturna.utils.log_utils import jt_logger
from juturna.meta._constants import JUTURNA_ENV_VAR_PREFIX
from juturna.utils.jt_utils._get_env_var import cast_env_value
from juturna.components.exceptions import EnvVarNotAllowedError


_logger = jt_logger('builder.utils')


def _resolve_env_var(
    key: str,
    value: str,
    node_name: str,
    local_arguments: dict,
    allowed_env_vars: frozenset[str] | None = None,
    env_vars: Mapping[str, str] | None = None,
) -> str:
    env_var_name = value[len(JUTURNA_ENV_VAR_PREFIX) :]
    default_value = local_arguments[key]

    # the variables given to the pipeline come first, and need no permission
    if env_vars is not None and env_var_name in env_vars:
        return cast_env_value(
            env_var_name, env_vars[env_var_name], default_value
        )

    # checked here, where every value is resolved, so that no configuration
    # (of a node, or of the warp in front of it) can get around the list
    if not _env_var_allowed(env_var_name, allowed_env_vars):
        raise EnvVarNotAllowedError(env_var_name, node_name)

    if env_var_name not in os.environ:
        error_msg = (
            f'env variable "{env_var_name}" is not set in node "{node_name}" '
            f'for config key "{key}" (found in config but not in environment)'
        )
        _logger.error(error_msg)

        raise ValueError(error_msg)

    return cast_env_value(env_var_name, os.environ[env_var_name], default_value)


def _env_var_allowed(name: str, allowed: Iterable[str] | None) -> bool:
    """
    Tell whether a variable of the process environment can be read: always
    when there is no list, otherwise when its name matches an entry of the
    list. An entry is a name, or a shell-style pattern (``MODEL_*``, ``*``),
    and letter case counts.
    """
    if allowed is None:
        return True

    return any(fnmatch.fnmatchcase(name, pattern) for pattern in allowed)


def _update_local_with_remote(local: dict, remote: dict) -> dict:
    merged_config = {k: remote.get(k, v) for k, v in local.items()}

    return merged_config


def _lazy_node_loaders(package_name: str, available_items: list) -> tuple:
    def __getattr__(name: str) -> type:
        if name in available_items:
            module_path = available_items[name]
            module = importlib.import_module(module_path, package=package_name)

            return getattr(module, name)

        raise AttributeError(f'no component {name} in {package_name!r}')

    def __dir__() -> list:
        return list(available_items.keys())

    return __getattr__, __dir__
