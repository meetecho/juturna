import pathlib
import json


def get_node_requirements(node: dict, folder: pathlib.Path) -> list[str]:
    node_folder = pathlib.Path(folder, node['type'], f'_{node["mark"]}')
    requirement_file = node_folder / 'requirements.txt'

    if not requirement_file.exists():
        return []

    with open(requirement_file) as f:
        return f.read().splitlines()


def collect_requirements(
    config_file: str, plugin_folders: list[str]
) -> list[str]:
    with open(config_file) as f:
        config = json.load(f)

    nodes = config['pipeline']['nodes']
    requirements = list()

    for plugin_folder in plugin_folders:
        nodes_folder = pathlib.Path(plugin_folder, 'nodes')

        for node in nodes:
            requirements += get_node_requirements(node, nodes_folder)

    return requirements
