"""
CLI registry

Commands are registered based on whether their required modules are installed. A
command for which its module fails to be imported will not be registered, so it
will not be available in the command line.
"""

import importlib


_MODULES = {
    cmd: None
    for cmd in [
        'launch',
        'validate',
        'serve',
        'create',
        'stub',
        'remotize',
        'require',
    ]
}


def _safe_reg(module_name: str, subparsers):
    try:
        _MODULES[module_name] = importlib.import_module(
            f'juturna.cli.commands.{module_name}'
        )
        _MODULES[module_name].setup_parser(subparsers)
    except ModuleNotFoundError:
        ...


def register_all(subparsers):
    """Register subparsers for all modules"""
    for module in _MODULES:
        _safe_reg(module, subparsers)


def command(cmd_name: str):
    """Return command caller function"""
    return _MODULES[cmd_name]._execute
