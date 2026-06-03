"""
Interactive pipeline builder

Use the CLI to interactively create a pipeline configuration and save it as
JSON file. This utility navigates all the plugin folders that are provided.

"""

import pathlib

import juturna as jt

from juturna.cli.commands._juturna_config_creator import PipelineBuilder


def setup_parser(subparsers):  # noqa: D103
    parser = subparsers.add_parser(
        'create',
        help='interactively create new pipeline configuration files',
    )

    parser.add_argument(
        '--plugins',
        '-p',
        action='append',
        type=str,
        help='juturna service pipeline folder',
    )


def _execute(args):
    args.plugins = args.plugins or list()

    args.plugins.append(pathlib.Path(jt.__path__[0], 'nodes'))

    args.plugins = list(map(lambda x: pathlib.Path(x).resolve(), args.plugins))
    origins = {f: 'local' for f in args.plugins[:-1]}
    origins[args.plugins[-1]] = 'built-in'

    builder = PipelineBuilder(args.plugins, origins)
    builder.run()
