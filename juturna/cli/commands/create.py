"""
Interactive pipeline builder

Use the CLI to interactively create a pipeline configuration and save it as
JSON file. This utility lists the nodes installed in the juturna.nodes,
juturna.extensions.nodes and juturna.contrib.<author>.nodes namespaces.

"""

from juturna.cli.commands._juturna_config_creator import PipelineBuilder


def setup_parser(subparsers):  # noqa: D103
    subparsers.add_parser(
        'create',
        help='interactively create new pipeline configuration files',
    )


def _execute(args):
    builder = PipelineBuilder()
    builder.run()
