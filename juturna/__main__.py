"""
Juturna CLI entrypoint

This module initializes the argument parser, registers all available subcommands
via the ``juturna.cli.commands`` registry, and dispatches execution to the
appropriate handler based on user input.

The Juturna CLI provides utilities to manage pipeline configuration files and
pipeline lifecycles.
"""

import argparse
import sys


from juturna.cli import commands


parser = argparse.ArgumentParser(
    prog='juturna',
    description=(
        'Collection of simple CLI utilities to manage pipeline configuration '
        'files and pipeline lifecycles.'
    ),
)

subparsers = parser.add_subparsers(
    dest='command', description='List of commands included in the juturna CLI'
)

commands.register_all(subparsers)
_ret = 0

args = parser.parse_args()

if command := args.command:
    delattr(args, 'command')
    _ret = commands.command(command)(args)
else:
    parser.print_help()

sys.exit(_ret)
