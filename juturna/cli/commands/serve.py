from juturna.cli.commands._juturna_service import run


def setup_parser(subparsers):  # noqa: D103
    # common_parser = _common_pipe_parser.common_parser()
    parser = subparsers.add_parser(
        'serve',
        help='instantiate and run the pipeline in the configuration file',
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
        help='set log level during pipeline execution'
    )


def _execute(args):
    run(args.host, args.port, args.folder, args.log_level)
