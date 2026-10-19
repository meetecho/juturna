"""
Serve the Juturna pipeline manager

Set up the Juturna pipeline manager and serve it on a provided host:port pair.
The service is spawned by targeting a running folder for all the created
pipelines, and log level, format, and destination file.

Every request must carry the service token as a bearer credential
(`Authorization: Bearer <token>`). The token is read from the
`JUTURNA_SERVICE_TOKEN` environment variable; when that is not set, a random
token is generated and printed on startup. `--no-auth` turns the check off,
for development or when another layer (a gateway, a service mesh) already
authenticates the clients.

Serving the Juturna manager requires Juturna to be installed with the
`httpwrapper` dependency group.
"""

from juturna.cli import _cli_utils
from juturna.cli.commands._juturna_service import run


def setup_parser(subparsers):  # noqa: D103
    parser = subparsers.add_parser(
        'serve',
        help='launch the Juturna pipeline manager service',
    )

    parser.add_argument(
        '--host',
        '-H',
        default='127.0.0.1',
        type=str,
        help='juturna service host address (default: 127.0.0.1)',
    )

    parser.add_argument(
        '--port',
        '-p',
        required=True,
        type=int,
        help='juturna service port',
    )

    parser.add_argument(
        '--folder',
        '-f',
        required=True,
        type=str,
        help='juturna service pipeline folder',
    )

    parser.add_argument(
        '--log-config',
        '-l',
        type=_cli_utils._is_file_ok,
        help='log configuration file',
    )

    parser.add_argument(
        '--dev',
        '-d',
        action='store_true',
        help='run service in development mode (allows cross-origin requests)',
    )

    parser.add_argument(
        '--no-auth',
        dest='auth',
        action='store_false',
        help='do not require the service token (only for development, or '
        'behind a layer that authenticates the clients)',
    )

    parser.add_argument(
        '--allow-env',
        '-e',
        action='append',
        default=list(),
        metavar='NAME',
        help='environment variable that pipeline configurations sent to the '
        'service can reference with $JT_ENV_ (repeatable, none by default)',
    )


def _execute(args):
    run(
        args.host,
        args.port,
        args.folder,
        args.log_config,
        args.dev,
        args.allow_env,
        args.auth,
    )
