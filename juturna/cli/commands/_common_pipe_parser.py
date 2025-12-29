import argparse

from juturna.cli import _cli_utils


def common_parser():
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument(
        '--log-level',
        '-l',
        type=str,
        default='DEBUG',
        choices=['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='set log level during pipeline execution',
    )

    parser.add_argument(
        '--config',
        '-c',
        required=True,
        metavar='FILE',
        type=_cli_utils._is_file_ok,
        help='pipeline json configuration file',
    )

    return parser
