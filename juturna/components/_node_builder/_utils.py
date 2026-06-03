import importlib
import os

from juturna.utils.log_utils import jt_logger
from juturna.meta._constants import JUTURNA_ENV_VAR_PREFIX
from juturna.utils.jt_utils._get_env_var import get_env_var


_logger = jt_logger('builder.utils')


def _resolve_env_var(
    key: str, value: str, node_name: str, local_arguments: dict
) -> str:
    env_var_name = value[len(JUTURNA_ENV_VAR_PREFIX) :]
    default_value = local_arguments[key]

    if env_var_name not in os.environ:
        error_msg = (
            f'env variable "{env_var_name}" is not set in node "{node_name}" '
            f'for config key "{key}" (found in config but not in environment)'
        )
        _logger.error(error_msg)

        raise ValueError(error_msg)

    return get_env_var(env_var_name, default_value)


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
