import pathlib
from juturna.utils.jt_utils import get_env_var


_VAR_DEFAULTS = {
    'JUTURNA_BASE_REPO': 'https://github.com/meetecho/juturna',
    'JUTURNA_HUB_URL': 'https://api.github.com/repos/meetecho/juturna/contents/plugins/',
    'JUTURNA_HUB_TOKEN': '',
    'JUTURNA_CACHE_DIR': str(
        pathlib.Path(pathlib.Path.home(), '.cache', 'juturna')
    ),
    'JUTURNA_LOCAL_PLUGIN_DIR': './plugins',
    'JUTURNA_THREAD_JOIN_TIMEOUT': 2.0,
    'JUTURNA_MAX_QUEUE_SIZE': 999,
}


def get_constant_var(var_name: str):
    return get_env_var(var_name, _VAR_DEFAULTS[var_name])


JUTURNA_BASE_REPO = get_constant_var('JUTURNA_BASE_REPO')
JUTURNA_HUB_URL = get_constant_var('JUTURNA_HUB_URL')
JUTURNA_CACHE_DIR = get_constant_var('JUTURNA_CACHE_DIR')
JUTURNA_HUB_TOKEN = get_constant_var('JUTURNA_HUB_TOKEN')
JUTURNA_LOCAL_PLUGIN_DIR = get_constant_var('JUTURNA_LOCAL_PLUGIN_DIR')
JUTURNA_THREAD_JOIN_TIMEOUT = get_constant_var('JUTURNA_THREAD_JOIN_TIMEOUT')
JUTURNA_MAX_QUEUE_SIZE = get_constant_var('JUTURNA_MAX_QUEUE_SIZE')
