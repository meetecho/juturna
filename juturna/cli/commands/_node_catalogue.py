"""
The node types a pipeline of this installation can use.

Types are listed without importing the node modules, which can be heavy
(models, native libraries): only the packages that declare the nodes are
imported, and the defaults come from the ``config.toml`` next to each node.
"""

import importlib
import importlib.util
import logging
import pathlib
import tomllib


logger = logging.getLogger('jt.catalogue')

# where the builder looks for nodes: a type without prefix is in the nodes
# package, the others carry the name of their namespace
_BUILTIN_PACKAGE = 'juturna.nodes'
_NAMESPACES = ('contrib', 'extensions')
_REGISTRY = '_AVAILABLE_PLUGINS'


def node_catalogue() -> list[dict]:
    """
    List the node types that can be named in a pipeline configuration.

    Returns
    -------
    list[dict]
        One entry per node type, sorted by type: ``type`` is the name to
        write in the configuration, ``description`` comes from the ``[meta]``
        table of the node ``config.toml`` (empty when it has none), and
        ``arguments`` are the configuration keys with their defaults.

    """
    entries = dict()

    for package_name, prefix in _node_packages():
        try:
            package = importlib.import_module(package_name)
        except Exception:
            # one broken package must not hide the others
            logger.warning(
                f'cannot read nodes of {package_name}', exc_info=True
            )

            continue

        registry = getattr(package, _REGISTRY, None)

        if not isinstance(registry, dict):
            continue

        for node_name, module_path in registry.items():
            node_type = '.'.join(p for p in (prefix, node_name) if p)
            entries[node_type] = _describe(node_type, module_path, package_name)

    return [entries[node_type] for node_type in sorted(entries)]


def _node_packages() -> list[tuple[str, str]]:
    """
    Find the packages that declare nodes, as pairs of the package to import
    and the prefix its nodes have in a configuration. A package declares
    nodes with an ``_AVAILABLE_PLUGINS`` table in its ``__init__.py``, which
    is looked for in the source, so that nothing else is imported.
    """
    packages = list()

    if _find_spec(_BUILTIN_PACKAGE) is not None:
        packages.append((_BUILTIN_PACKAGE, ''))

    for namespace in _NAMESPACES:
        spec = _find_spec(f'juturna.{namespace}')

        if spec is None:
            continue

        for location in spec.submodule_search_locations or ():
            root = pathlib.Path(location)

            for init in sorted(root.rglob('__init__.py')):
                parts = init.parent.relative_to(root).parts

                if not parts or not _declares_nodes(init):
                    continue

                prefix = '.'.join((namespace, *parts))
                packages.append((f'juturna.{prefix}', prefix))

    return packages


def _find_spec(name: str):
    try:
        return importlib.util.find_spec(name)
    except (ImportError, ValueError):
        return None


def _declares_nodes(init: pathlib.Path) -> bool:
    try:
        return _REGISTRY in init.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return False


def _describe(node_type: str, module_path: str, package_name: str) -> dict:
    entry = {'type': node_type, 'description': '', 'arguments': dict()}

    try:
        # resolves the module of the node without importing it
        spec = importlib.util.find_spec(module_path, package=package_name)
        config_path = pathlib.Path(spec.origin).parent / 'config.toml'

        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
    except Exception:
        logger.warning(
            f'cannot read the defaults of {node_type}', exc_info=True
        )

        return entry

    arguments = config.get('arguments')
    meta = config.get('meta')

    if isinstance(arguments, dict):
        entry['arguments'] = arguments

    if isinstance(meta, dict) and isinstance(meta.get('description'), str):
        entry['description'] = meta['description']

    return entry
