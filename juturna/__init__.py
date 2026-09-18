# noqa: D104
import juturna.names as names
import juturna.components as components
import juturna.utils as utils
import juturna.hub as hub
import juturna.meta as meta
import juturna.payloads as payloads
import juturna.remotizer as remotizer

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
    Lazily import juturna.nodes on first access (PEP 562).

    juturna.nodes.source/sink eagerly import every built-in node,
    including its runtime dependency (av, for every RTP/file audio-video
    node) - importing it unconditionally here would make a plain
    `import juturna` require av even for code that never touches a
    single node (e.g. juturna.components.Node/Pipeline used directly, or
    a deployment where av has no available build at all). Pipeline
    itself never needs this: node classes are resolved by name via
    importlib (juturna.components._node_builder), never through this
    package's own namespace.
    """
    if name == 'nodes':
        import juturna.nodes

        globals()['nodes'] = juturna.nodes
        return juturna.nodes

    raise AttributeError(f"module 'juturna' has no attribute {name!r}")
