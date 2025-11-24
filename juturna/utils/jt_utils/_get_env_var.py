import os
from juturna.utils.log_utils import jt_logger

_logger = jt_logger()


def get_env_var(var_name: str, defaults: dict):
    env_value = os.environ.get(var_name)

    if env_value is None:
        return defaults[var_name]

    default_value = defaults[var_name]

    try:
        target_type = type(default_value)

        return (
            target_type(env_value)
            if target_type is not bool
            else env_value.lower() in ('true', '1', 'yes')
        )

    # AttributeError should never happen (env_value is always not None here)
    except (ValueError, TypeError) as conv_err:
        _logger.error(
            f'Invalid value for environment variable {var_name}: {env_value}. '
            f'Expected type: {type(default_value).__name__}'
        )
        raise RuntimeError('Invalid value type for env_var') from conv_err
