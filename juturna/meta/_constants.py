import os
import pathlib


_VAR_DEFAULTS = {
    'JUTURNA_BASE_REPO': 'https://github.com/meetecho/juturna',
    'JUTURNA_HUB_URL': 'https://api.github.com/repos/meetecho/juturna/contents/plugins/',
    'JUTURNA_HUB_TOKEN': None,
    'JUTURNA_CACHE_DIR': str(
        pathlib.Path(pathlib.Path.home(),'.cache', 'juturna'))
}


def _get_env_var(var_name: str) -> str:
    return os.environ.get(var_name, _VAR_DEFAULTS[var_name])


JUTURNA_BASE_REPO = _get_env_var('JUTURNA_BASE_REPO')
JUTURNA_HUB_URL   = _get_env_var('JUTURNA_HUB_URL')
JUTURNA_CACHE_DIR = _get_env_var('JUTURNA_CACHE_DIR')
JUTURNA_HUB_TOKEN = _get_env_var('JUTURNA_HUB_TOKEN')
