import importlib
import inspect
import tomllib
import pathlib
import os

from collections.abc import Iterable


_NODE_IMPORT_PATH = 'juturna.nodes'
_NODE_IMPORT_MASK = '{}._{}.{}'


def node(
    node_type: str, node_name: str, import_prefix: str = _NODE_IMPORT_PATH
) -> tuple[type | None, dict]:
    """
    Constructs a node module based on the given node type and name.

    This function is responsible for dynamically constructing a node module
    using the provided node type and node name. The full module path is built
    by combining the `import_prefix` with the node type and name. The function
    then uses this path to load and return the node's class along with its
    configuration.

    Parameters
    ----------
    node_type : str
        The type of the node (e.g., "proc", "source", "sink").
    node_name : str
        The name of the node to be loaded.
    import_prefix : str, optional
        The import prefix for the node (default is 'juturna.nodes').

    Returns
    -------
    Tuple[type, dict]
        A tuple containing the node class and its configuration dictionary.

    Examples
    --------
    >>> launcher, config = node('proc', 'silero_vad')

    """
    _node_module_path = f'{import_prefix}.{_NODE_IMPORT_MASK}'
    _node_module_path = _node_module_path.format(
        node_type, node_name, node_name
    )

    return _build(_node_module_path, node_name)


def _build(_item_path: str, _item_type: str) -> tuple[type | None, dict]:
    """
    Build a module by discovering its classes and configuration.

    This helper function combines several steps to build a module: discovering
    all the classes in a given import path, identifying the correct launcher
    class based on the module's type, and then loading any associated
    configuration data. The configuration is expected to be stored in a TOML
    file located in the module's directory.

    Parameters
    ----------
    _item_path : str
        The full import path for the module.
    _item_type : str
        The type of the item being loaded.

    Returns
    -------
    Tuple[type, dict]
        A tuple containing the module class and its configuration dictionary.

    """
    _classes = _discover_classes(_item_path)
    _module_launcher = _get_module_launcher(_classes, _item_type)
    _module_configuration = _get_module_conf(_module_launcher)

    return _module_launcher, _module_configuration


def _discover_classes(_import_path: str) -> list:
    """
    Discovers and returns a list of classes in a given module.

    This function imports a module from the specified path and inspects it to
    identify all classes defined within it. It filters out any private or
    protected classes (those whose names start with an underscore). The primary
    use of this function is to provide a list of candidate classes that could
    serve as the main entry point (launcher) for a node.

    Parameters
    ----------
    _import_path : str
        The full import path of the module to inspect.

    Returns
    -------
    list
        A list of tuples, each tuple contains a class name and its object.

    """
    _item_module = importlib.import_module(_import_path)

    return [
        m for m in inspect.getmembers(_item_module) if not m[0].startswith('_')
    ]


def _get_module_launcher(_classes: Iterable, _item_type: str) -> type | None:
    """
    Retrieves the main launcher class from a list of discovered classes.

    This function iterates over the list of classes identified by
    `_discover_classes`, looking for the class whose module matches the
    specified item type. The correct launcher class is typically the one whose
    module name matches the node being loaded. If no such class is found, the
    function returns `None`.

    Parameters
    ----------
    _classes : list
        A list of tuples containing class names and class objects.
    _item_type : str
        The type of item to match against the class module name.

    Returns
    -------
    class
        The class that matches the module type, or None if no match is found.

    """
    for _c in _classes:
        try:
            if _c[1].__module__.split('.')[-1] == _item_type:
                return _c[1]
        except Exception:
            ...
    else:
        return None


def _get_module_conf(_module_launcher: type | None) -> dict:
    """
    Loads the configuration for a module if a config.toml file is found.

    This function attempts to load a TOML configuration file located in the
    same directory as the module's launcher class. If a `config.toml` file is
    found, it is parsed and returned as a dictionary. If no configuration file
    is found or if an error occurs while reading it, an empty dictionary is
    returned instead.

    Parameters
    ----------
    _module_launcher : class
        The launcher class whose configuration is being retrieved.

    Returns
    -------
    dict
        A dictionary containing the configuration for the module, or an empty
        dictionary if no configuration file is found.

    """
    _module_path = inspect.getfile(_module_launcher)
    _module_path = pathlib.Path(_module_path).parent
    _config_file = _module_path / 'config.toml'

    if _config_file.exists():
        with open(_config_file, 'rb') as f:
            conf = tomllib.load(f)
        return conf

    return dict()


def discover_components(import_prefix: str | None = None) -> dict:
    _prefix_paths = _get_full_prefix(import_prefix)
    components = {
        'nodes': {
            t.name: [s_t.name for s_t in t.glob('*') if s_t.is_dir()]
            for t in _prefix_paths['nodes']
            if t.name != '__pycache__'
        }
    }

    return components


def _get_full_prefix(prefix: str | None = None) -> dict:
    node_path = pathlib.Path(
        prefix or _NODE_IMPORT_PATH.replace('.', os.sep),
        'nodes' if prefix else '',
    )

    return {'nodes': [p for p in node_path.glob('*') if p.is_dir()]}
