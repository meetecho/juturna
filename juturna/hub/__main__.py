"""
Juturna Hub utility entrypoint

This module offers the basic functionalities for the Juturna Hub. It is highly
experimental, and if development continues it will later be moved into the
main CLI.
"""

import argparse

from juturna import hub


_COMMANDS = {
    'list_plugins': hub.list_plugins,
    'download_node': hub.download_node,
    'download_pipeline': hub.download_pipeline,
}

parser = argparse.ArgumentParser(prog='hub')

parser.add_argument(
    '--repository-url',
    '-r',
    type=str,
    help='the url of the repository to query (default to base juturna repo)',
)
parser.add_argument(
    '--authenticate',
    '-a',
    action='store_true',
    help='authenticate the query to the repository using the env token',
)

subparsers = parser.add_subparsers(dest='_command')

_list_parser = subparsers.add_parser(
    'list_plugins',
    help='list all available plugins in the specified repository',
)

_dwl_parser = subparsers.add_parser(
    'download',
    help='download a plugin (either a single node or a full pipeline)',
)

_dwl_group = _dwl_parser.add_mutually_exclusive_group()
_dwl_group.add_argument(
    '--node-name',
    '-n',
    type=str,
    help='name of the node to download (make sure it contains the node type)',
)
_dwl_group.add_argument(
    '--pipe-name', type=str, help='name of the pipe to download'
)

_dwl_parser.add_argument(
    '--destination-folder',
    '-d',
    type=str,
    help='destination folder for the plugin (defaulted to ./plugins)',
)
_dwl_parser.add_argument(
    '--force',
    '-f',
    action='store_true',
    help='will force re-download if the plugin already exists',
)

args = parser.parse_args()

arguments = args.__dict__
_command = arguments['_command']

del arguments['_command']

match _command:
    case 'list_plugins':
        plugins = hub.list_plugins(**arguments)

        print(plugins)
    case 'download':
        if arguments['node_name']:
            del arguments['pipe_name']

            hub.download_node(**arguments)
        else:
            del arguments['node_name']

            hub.download_pipeline(**arguments)
