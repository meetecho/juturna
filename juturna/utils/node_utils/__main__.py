import argparse

from juturna.utils import node_utils


_COMMANDS = {
    'stub': node_utils.node_stub
}

parser = argparse.ArgumentParser(prog='node utils')

subparsers = parser.add_subparsers(dest='_command')

_stub_parser = subparsers.add_parser(
    'stub',
    help='list all available plugins in the specified repository')

_stub_parser.add_argument(
    '--node-name', '-n',
    type=str,
    help='node name, used for folder and module')
_stub_parser.add_argument(
    '--node-type', '-t',
    type=str,
    help='node type')
_stub_parser.add_argument(
    '--node-class', '-N',
    type=str,
    help='node class name, used for class name')
_stub_parser.add_argument(
    '--destination-folder', '-d',
    type=str,
    default='./plugins',
    help='destination folder for the plugin (defaulted to ./plugins)')

args = parser.parse_args()
arguments = args.__dict__
_command = arguments['_command']

match _command:
    case 'stub':
        node_utils.node_stub(
            node_name=arguments['node_name'],
            node_type=arguments['node_type'],
            node_class_name=arguments['node_class'],
            destination=arguments['destination_folder'])