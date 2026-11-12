import os
from typing import TypeVar
from juturna.utils.log_utils import jt_logger

T = TypeVar('T')

_logger = jt_logger()


def get_env_var[T](var_name: str, default_value: T) -> T:
    env_value = os.environ.get(var_name)

    if env_value is None:
        return default_value

    return cast_env_value(var_name, env_value, default_value)


def cast_env_value[T](var_name: str, env_value: str, default_value: T) -> T:
    """
    Convert the text of a variable to the type of its default value. For a
    boolean, ``true``, ``1`` and ``yes`` (in any case) are true.
    """
    try:
        target_type = type(default_value)

        return (
            target_type(env_value)
            if target_type is not bool
            else env_value.lower() in ('true', '1', 'yes')
        )

    # AttributeError should never happen (env_value is always not None here)
    except (ValueError, TypeError):
        _logger.error(
            f'Invalid value for environment variable {var_name}. '
            f'Expected type: {type(default_value).__name__}'
        )
        # not chained: the conversion error quotes the value, which may be
        # a secret, and would end up in the tracebacks that are logged
        raise RuntimeError('Invalid value type for env_var') from None
