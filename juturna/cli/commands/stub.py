"""
Create node stub

This command creates a node skeleton, starting from basic pieces of information
such as node name, contrib package, and node class if it cannot be
automatically inferred from the name. Author info also included.

The command is meant to be executed in the root of a node repository: the node
is created in src/juturna/contrib/<package>/nodes/, and registered in the
__init__.py file of the nodes package.
"""

from juturna.cli.commands import _node_stub


def setup_parser(subparsers):  # noqa: D103
    parser = subparsers.add_parser(
        'stub',
        help='create a custom node skeleton',
    )

    parser.add_argument(
        '--node-name',
        '-n',
        type=str,
        required=True,
        help='node name, used for folder and module',
    )
    parser.add_argument(
        '--package',
        '-p',
        type=str,
        required=True,
        help='contrib package name (juturna.contrib.<package>.nodes)',
    )
    parser.add_argument(
        '--node-class',
        '-N',
        type=str,
        help='node class name, used for class name',
    )
    parser.add_argument(
        '--author',
        '-a',
        type=str,
        default='not provided',
        help='node author name',
    )
    parser.add_argument(
        '--email',
        '-e',
        type=str,
        default='not provided',
        help='node author email',
    )
    parser.add_argument(
        '--destination-folder',
        '-d',
        type=str,
        default='./src',
        help='source folder of the node repository (defaulted to ./src)',
    )


def _execute(args):
    _node_stub.node_stub(**args.__dict__)
