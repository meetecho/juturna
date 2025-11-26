import os
from typing import TypeVar
from juturna.utils.log_utils import jt_logger

T = TypeVar("T")

_logger = jt_logger()


def get_env_var[T](var_name: str, default_value: T) -> T:
    env_value = os.environ.get(var_name)

    if env_value is None:
        return default_value

    try:
        target_type = type(default_value)

        return (
            target_type(env_value)
            if target_type is not bool
            else env_value.lower() in ("true", "1", "yes")
        )

    # AttributeError should never happen (env_value is always not None here)
    except (ValueError, TypeError) as conv_err:
        _logger.error(
            f"Invalid value for environment variable {var_name}. "
            f"Expected type: {type(default_value).__name__}"
        )
        raise RuntimeError("Invalid value type for env_var") from conv_err
