"""
Aggregate requirements for a pipeline

Collect all the requirements for plugin nodes in a pipeline. The command gives
the option to dump the package list in a file, or even store them within the
pipeline configuration file, under the `requirements` field.
"""

import json


from juturna.cli.commands import _common_pipe_parser
from juturna.cli.commands._require_tools import collect_requirements


def setup_parser(subparsers):  # noqa: D103
    common_parser = _common_pipe_parser.common_parser()
    parser = subparsers.add_parser(
        'require',
        parents=[common_parser],
        help='collect all the required packages for a pipeline',
    )

    parser.add_argument(
        '--plugin-dir',
        '-p',
        nargs='+',
        required=True,
        type=str,
        help='plugin folders (at least one is required)',
    )

    parser.add_argument(
        '--add-extra',
        '-a',
        action='store_true',
        help='add collected dependencies to configuration file',
    )

    parser.add_argument(
        '--save',
        '-s',
        type=str,
        help='where to save the collected dependencies',
    )


def _execute(args):
    pipe_config_file = args.config
    plugin_folders = args.plugin_dir

    requirements = collect_requirements(pipe_config_file, plugin_folders)

    if len(requirements) == 0:
        print('No extra dependency found!')

        return

    print('The following requirements were found:\n')

    list(map(print, requirements))

    print()

    if args.add_extra:
        with open(pipe_config_file) as f:
            config = json.load(f)
            config['requirements'] = requirements

        with open(pipe_config_file, 'w') as f:
            json.dump(config, f, indent=2)

        print('Requirements saved to configuration file')

    if args.save:
        with open(args.save, 'w') as f:
            f.write('\n'.join(requirements))
            f.write('\n')

        print(f'Requirements saved to {args.save}')
