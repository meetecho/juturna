"""
Start a remote service to remotize nodes

This command can be used to instantiate concrete nodes that can be invoked
through the remote juturna service.
"""

from juturna.cli import _cli_utils
from juturna.cli.commands._juturna_remote_service import serve


def setup_parser(subparsers):  # noqa: D103
    parser = subparsers.add_parser(
        'remotize',
        help='start the remote node service',
    )

    parser.add_argument(
        '--node-name', '-n', required=True, help='name of the node to run'
    )

    parser.add_argument(
        '--node-mark', '-m', required=True, help='mark of the node to run'
    )

    parser.add_argument(
        '--plugin-dir', '-P', required=True, help='path to plugins directory'
    )

    parser.add_argument(
        '--pipe-name', '-N', default='warped_node', help='pipeline name context'
    )

    parser.add_argument(
        '--port', '-p', type=int, default=50051, help='port to listen on'
    )

    parser.add_argument(
        '--default-config',
        '-c',
        metavar='FILE',
        type=_cli_utils._is_file_ok,
        required=False,
        help='default configuration as JSON string',
    )

    parser.add_argument(
        '--max-workers',
        '-w',
        type=int,
        default=10,
        help='maximum number of worker threads',
    )


def _execute(args):
    serve(args)
