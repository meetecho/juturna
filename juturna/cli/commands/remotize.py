"""
Start a remote service to remotize nodes

This command can be used to instantiate concrete nodes that can be invoked
through the remote juturna service. One remote node can serve several
pipelines: each client warp node gets its own state, and the node is
configured once, at startup, with the default configuration file.
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
        '--node-type', '-t', required=True, help='type of the node to run'
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

    parser.add_argument(
        '--max-requests',
        type=int,
        default=None,
        help='requests accepted at once, in progress or waiting for a '
        'worker; more are refused (default: 10 for each worker)',
    )

    parser.add_argument(
        '--max-clients',
        type=int,
        default=1024,
        help='sticky clients the service keeps a state for; new ones are '
        'refused beyond that (default: 1024)',
    )

    parser.add_argument(
        '--strict',
        action='store_true',
        help='fail requests with DATA_LOSS instead of leaving out, with a '
        'warning, what cannot be sent to the client',
    )

    parser.add_argument(
        '--log-level',
        '-l',
        type=str,
        default='INFO',
        choices=['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='log level of the service and the node (default: INFO)',
    )


def _execute(args):
    return serve(args)
