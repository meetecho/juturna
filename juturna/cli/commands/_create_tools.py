import pathlib
import tomllib


_TYPE_MAP = {
    bool: 'boolean',
    int: 'integer',
    float: 'float',
    str: 'string',
    dict: 'dictionary',
    list: 'list',
}


def discover_nodes(node_folder: str) -> dict:
    node_registry = dict()

    folder = pathlib.Path(node_folder)

    if not folder.exists():
        raise FileNotFoundError(f'node folder {node_folder} does not exist')

    for node_type_dir in folder.iterdir():
        if not node_type_dir.is_dir():
            continue

        nodes = discover_node_marks(str(node_type_dir))

        if nodes:
            node_registry[node_type_dir.name] = nodes

    return node_registry


def discover_node_marks(node_folder: str) -> dict:
    folder = pathlib.Path(node_folder)
    registry = dict()

    marks = folder.glob('_*')

    for mark_dir in filter(lambda d: d.is_dir(), marks):
        mark = mark_dir.name[1:]
        config_path = mark_dir / 'config.toml'

        if not config_path.exists():
            continue

        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
            arguments = config.get('arguments', {})

            registry[mark] = {
                'arguments': {
                    arg_name: {
                        'default': arg_value,
                        'type': _TYPE_MAP.get(type(arg_value)),
                    }
                    for arg_name, arg_value in arguments.items()
                }
            }

    return registry


def get_types(nodes: dict) -> list[str]:
    return sorted(nodes.keys())


def get_marks(nodes: dict, node_type: str) -> list[str]:
    return sorted(nodes.get(node_type, {}).keys())


def get_config(nodes: dict, node_type: str, node_mark: str) -> dict | None:
    return nodes.get(node_type, {}).get(node_mark)
