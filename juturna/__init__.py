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
    """
    Lazily import juturna.nodes, juturna.hub and juturna.remotizer on first
    access (PEP 562).

    Each of them pulls in dependencies that a plain `import juturna` must
    not require: juturna.nodes.source/sink eagerly import every built-in
    node, including its runtime dependency (av, for every RTP/file
    audio-video node); juturna.hub needs requests; juturna.remotizer needs
    grpc and protobuf. Importing them unconditionally here would make code
    that never touches them (e.g. juturna.components.Node/Pipeline used
    directly, or a Pyodide deployment where none of these has a build)
    fail on the first `import juturna.<anything>`. Pipeline itself never
    needs them: node classes are resolved by name via importlib
    (juturna.components._node_builder), never through this package's own
    namespace.
    """
    if name in ('nodes', 'hub', 'remotizer'):
        module = importlib.import_module(f'juturna.{name}')

        globals()[name] = module
        return module

    raise AttributeError(f"module 'juturna' has no attribute {name!r}")
