"""
Serve the Juturna pipeline manager

Set up the Juturna pipeline manager and serve it on a provided host:port pair.
The service is spawned by targeting a running folder for all the created
pipelines, and log level, format, and destination file.

Serving the Juturna manager requires Juturna to be installed with the
`httpwrapper` dependency group.
"""

from juturna.cli.commands._juturna_service import run


def setup_parser(subparsers):  # noqa: D103
    parser = subparsers.add_parser(
        'serve',
        help='launch the Juturna pipeline manager service',
    )

    parser.add_argument(
        '--host',
        '-H',
        required=True,
        type=str,
        help='juturna service host address',
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
        '--log-level',
        '-l',
        type=str,
        default='DEBUG',
        choices=['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='set log level during pipeline execution',
    )

    parser.add_argument(
        '--log-format',
        '-F',
        type=str,
        default='full',
        choices=[
            'simple',
            'colored',
            'full',
            'compact',
            'development',
            'minimal',
            'json',
        ],
        help='log format',
    )

    parser.add_argument(
        '--log-file', '-L', type=str, help='log file destination'
    )


def _execute(args):
    run(
        args.host,
        args.port,
        args.folder,
        args.log_level,
        args.log_format,
        args.log_file,
    )
