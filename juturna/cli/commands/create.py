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
    if args.plugins is None:
        args.plugins = [jt.meta.JUTURNA_LOCAL_PLUGIN_DIR]

    # add built-in nodes from juturna installation folder
    args.plugins.append(pathlib.Path(jt.__path__[0], 'nodes'))

    args.plugins = list(map(lambda x: pathlib.Path(x).resolve(), args.plugins))

    builder = PipelineBuilder(args.plugins)
    builder.run()
