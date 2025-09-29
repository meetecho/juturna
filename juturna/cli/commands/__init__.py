"""CLI registry"""

from juturna.cli.commands import launch
from juturna.cli.commands import validate


_COMMANDS = {
    'launch': launch._execute,
    'validate': validate._execute
}


def register_all(subparsers):
    """Register command subparsers to main parser"""
    launch.setup_parser(subparsers)
    validate.setup_parser(subparsers)


def command(cmd_name: str):
    """Return command caller function"""
    return _COMMANDS[cmd_name]
