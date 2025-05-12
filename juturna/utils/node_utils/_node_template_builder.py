import pathlib
import warnings


def node_stub(node_name: str,
              node_type: str,
              node_class_name: str = None,
              destination: str = './plugins'):
    node_destination = pathlib.Path(
        destination, 'nodes', node_type, f'_{node_name}')

    if node_destination.exists():
        warnings.warn(
            f'Node {node_name} already exists in {node_destination}. '
            'Please choose a different name or delete the existing node.',
            UserWarning)

        return

    node_destination.mkdir(parents=True)
    base_path = pathlib.Path(__file__).parent

    template_path = base_path / 'basic_node.template'
    config_path = base_path / 'basic_config.template'

    with open(template_path, 'r') as template_file:
        template = template_file.read()

    if node_class_name is None:
        node_class_name = ''.join(
            x.capitalize() for x in node_name.split('_'))

    template = template.replace('$_node_class_name', node_class_name)
    template = template.replace('$_node_type', node_type)

    node_file_path = pathlib.Path(node_destination, f'{node_name}.py')

    with open(node_file_path, 'w') as node_file:
        node_file.write(template)

    with open(config_path, 'r') as config_content:
        config = config_content.read()

    with open(pathlib.Path(node_destination, 'config.toml'), 'w') as cfg_file:
        cfg_file.write(config)

    open(pathlib.Path(node_destination, 'requirements.txt'), 'a').close()