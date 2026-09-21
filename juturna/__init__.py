# noqa: D104
import importlib

import juturna.names as names
import juturna.components as components
import juturna.utils as utils
import juturna.meta as meta
import juturna.payloads as payloads

import juturna.utils.log_utils as log


__app_name__ = 'juturna'
__version__ = '2.1.1'

__all__ = [
    'names',
    'components',
    'nodes',
    'utils',
    'log',
    'meta',
    'hub',
    'remotizer',
    'payloads',
]


def __getattr__(name: str):
    """Import juturna.nodes, juturna.hub and juturna.remotizer on first use"""
    if name in ('nodes', 'hub', 'remotizer'):
        module = importlib.import_module(f'juturna.{name}')

        globals()[name] = module
        return module

    raise AttributeError(f"module 'juturna' has no attribute {name!r}")
