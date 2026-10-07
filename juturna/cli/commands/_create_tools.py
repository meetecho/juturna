import importlib
import importlib.resources
import importlib.util
import pathlib
import pkgutil
import tomllib
import types


_TYPE_MAP = {
    bool: 'boolean',
    int: 'integer',
    float: 'float',
    str: 'string',
    dict: 'dictionary',
    list: 'list',
}

# node packages, with the prefix the node builder expects in the node type
# and the origin label shown to the user; contrib packages are added at
# discovery time, one for each juturna.contrib.<author>.nodes package
_NODE_NAMESPACES = {
    'juturna.nodes': ('', 'built-in'),
    'juturna.extensions.nodes': ('extensions.nodes', 'extensions'),
}


def discover_nodes() -> dict:
    """
    Collect the nodes available in the juturna node namespaces

    Returns a dictionary keyed by node type, formatted as the node builder
    expects it in a pipeline configuration (``AudioRtp``,
    ``extensions.nodes.MyNode``, ``contrib.author.nodes.MyNode``). Namespaces
    that are not installed are skipped.
    """
    registry = dict()
    namespaces = _NODE_NAMESPACES | _contrib_namespaces()

    for package_name, (type_prefix, origin) in namespaces.items():
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            continue

        registry.update(_discover_package(package, type_prefix, origin))

    return registry


def _contrib_namespaces() -> dict:
    try:
        contrib = importlib.import_module('juturna.contrib')
    except ImportError:
        return dict()

    return {
        f'juturna.contrib.{author.name}.nodes': (
            f'contrib.{author.name}.nodes',
            f'contrib.{author.name}',
        )
        for author in pkgutil.iter_modules(contrib.__path__)
        if author.ispkg
    }


def _discover_package(
    package: types.ModuleType, type_prefix: str, origin: str
) -> dict:
    registry = dict()

    for node_name in getattr(package, '__all__', []):
        config_path = _node_config_path(package, node_name)

        if config_path is None or not config_path.is_file():
            continue

        with open(config_path, 'rb') as f:
            arguments = tomllib.load(f).get('arguments', {})

        node_type = '.'.join(p for p in (type_prefix, node_name) if p)
        registry[node_type] = {
            'origin': origin,
            'arguments': {
                arg_name: {
                    'default': arg_value,
                    'type': _TYPE_MAP.get(type(arg_value)),
                }
                for arg_name, arg_value in arguments.items()
            },
        }

    for sub in pkgutil.iter_modules(package.__path__):
        if not sub.ispkg or sub.name.startswith('_'):
            continue

        try:
            sub_package = importlib.import_module(
                f'{package.__name__}.{sub.name}'
            )
        except ImportError:
            continue

        sub_prefix = '.'.join(p for p in (type_prefix, sub.name) if p)
        registry.update(_discover_package(sub_package, sub_prefix, origin))

    return registry


def _node_config_path(
    package: types.ModuleType, node_name: str
) -> pathlib.Path | None:
    """
    Locate the config.toml file of a node

    Node packages map their node names to module paths, so the node module can
    be located without importing it (and its dependencies). Packages without
    that mapping fall back to importing the node class.
    """
    module_path = getattr(package, '_AVAILABLE_PLUGINS', {}).get(node_name)

    try:
        if module_path is not None:
            spec = importlib.util.find_spec(
                importlib.util.resolve_name(module_path, package.__name__)
            )

            if spec is None or spec.origin is None:
                return None

            return pathlib.Path(spec.origin).parent / 'config.toml'

        node_class = getattr(package, node_name)
        resource = importlib.resources.files(node_class.__module__)

        return pathlib.Path(str(resource / 'config.toml'))
    except Exception:
        return None
