"""
Pipeline validation module

Validate a pipeline from the CLI. Provide the pipeline configuration, and the
module will analyse its content, checking if the pipeline is properly configured
and all its components are available.

"""

import json
import pathlib
import typing
import tomllib

import juturna as jt

from juturna.cli import _cli_utils
from juturna.cli.commands import _common_pipe_parser
from juturna.cli.commands._validation_tools import Check
from juturna.cli.commands._validation_tools import ValidationPipe
from juturna.cli.commands._validation_tools import ValidationError
from juturna.cli.commands._validation_tools import DAG
from juturna.cli.commands._validation_tools import warn


def setup_parser(subparsers):  # noqa: D103
    common_parser = _common_pipe_parser.common_parser()
    parser = subparsers.add_parser(
        'validate',
        parents=[common_parser],
        help='scan a configuration file and check its validity',
    )

    parser.add_argument(
        '--deep',
        '-d',
        action='store_true',
        help='check node config items against their default config files',
    )

    parser.add_argument(
        '--plugin-folder',
        '-p',
        metavar='DIR',
        type=_cli_utils._is_dir_ok,
        default='./plugins',
        help='directory where node plugin nodes are stored',
    )

    parser.add_argument(
        '--report',
        '-r',
        metavar='FILE',
        help='save json report of the validation test',
    )


def _execute(args):
    validation_pipe = ValidationPipe()

    cfg_path = pathlib.Path(args.config)
    plugins_root = pathlib.Path(args.plugin_folder)

    def _check_json(file_path) -> bool:
        try:
            _load_pipeline(file_path)

            return True
        except ValidationError:
            return False

    validation_pipe.add_check(Check('JSON well formed', _check_json), cfg_path)

    data = _load_pipeline(cfg_path)

    validation_pipe.add_check(
        Check('Configuration structure', _check_structure), data
    )

    pipeline = data['pipeline']
    nodes = pipeline['nodes']
    links = pipeline['links']

    validation_pipe.add_check(
        Check('Nodes well formed', _check_nodes_well_formed), nodes
    ).add_check(
        Check('Links well formed', _check_links_well_formed), links
    ).add_check(
        Check('DAG properly formed', _build_dag), nodes, links
    ).add_check(
        Check('DAG properties', _check_dag_properties),
        _build_dag(nodes, links),
        {n['name']: n['type'] for n in nodes},
    )

    for n in nodes:
        validation_pipe.add_check(
            Check(f'Node config {n["name"]}', _deep_check_node),
            n,
            plugins_root,
            active=args.deep,
        )

    validation_pipe.run_checks()
    validation_pipe.dag = _build_dag(nodes, links)

    if args.report:
        with open(args.report, 'w') as f:
            f.write(validation_pipe.to_json())


def _load_pipeline(cfg_path: pathlib.Path) -> dict[str, typing.Any]:
    try:
        with open(cfg_path) as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f'Cannot read JSON: {exc}') from None


def _check_structure(data: dict[str, typing.Any]) -> None:
    if 'pipeline' not in data:
        raise ValidationError("Top-level key 'pipeline' missing")

    pl = data['pipeline']

    for key in ('nodes', 'links'):
        if key not in pl:
            raise ValidationError(f'pipeline.{key} missing')


def _check_nodes_well_formed(nodes: list[dict[str, typing.Any]]) -> None:
    required = {'name', 'type', 'mark'}

    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValidationError(f'nodes[{idx}] is not an object')

        missing = required - node.keys()

        if missing:
            raise ValidationError(f'nodes[{idx}] missing keys: {missing}')


def _check_links_well_formed(links: list[dict[str, typing.Any]]) -> None:
    required = {'from', 'to'}

    for idx, link in enumerate(links):
        if not isinstance(link, dict):
            raise ValidationError(f'links[{idx}] is not an object')

        missing = required - link.keys()

        if missing:
            raise ValidationError(f'links[{idx}] missing keys: {missing}')


def _build_dag(nodes: list[dict], links: list[dict]) -> DAG:
    dag = DAG()

    for n in nodes:
        dag.add_node(n['name'])

    for link in links:
        dag.add_edge(link['from'], link['to'])

    return dag


def _check_dag_properties(dag: DAG, name_to_type: dict[str, str]) -> None:
    """No cycles, sources have no predecessors, sinks have no successors."""
    if dag.has_cycle():
        raise ValidationError('Pipeline links contain a cycle → not a DAG')

    in_degree = dag.in_degree()
    out_degree = dag.out_degree()

    non_source_zero_in = [
        n
        for n, d in in_degree.items()
        if d == 0 and name_to_type[n] != 'source'
    ]

    if non_source_zero_in:
        raise ValidationError(
            f'Non-source nodes with no input links: {non_source_zero_in}'
        )

    non_sink_non_zero_out = [
        n for n, d in out_degree.items() if d != 0 and name_to_type[n] == 'sink'
    ]

    if non_sink_non_zero_out:
        warn(f'Sink nodes with output links: {non_sink_non_zero_out}')


def _deep_check_node(node: dict, plugins_root: pathlib.Path) -> None:
    """
    Ensure every key inside node['configuration'] exists in the corresponding
    plugin default file: plugins/nodes/<type>/_<name>/config.toml
    """
    nodetype = node['type']
    nodename = node['mark']
    cfg = node.get('configuration') or {}
    if not cfg:
        return

    builtin_path = (
        pathlib.Path(jt.__file__).parent
        / 'nodes'
        / nodetype
        / f'_{nodename}'
        / 'config.toml'
    )

    external_path = pathlib.Path(
        plugins_root, 'nodes', nodetype, f'_{nodename}', 'config.toml'
    )

    if builtin_path.exists():
        defaults_file = builtin_path
    elif external_path.exists():
        defaults_file = external_path
    else:
        raise ValidationError(
            f"Deep check: no defaults file for node '{nodename}' "
            f'(checked {builtin_path.relative_to(builtin_path.anchor)} and '
            f'{external_path.relative_to(plugins_root.parent)})'
        )

    try:
        with defaults_file.open('rb') as fh:
            defaults = tomllib.load(fh)['arguments']
    except Exception as exc:
        raise ValidationError(
            f'Cannot parse TOML defaults {defaults_file}: {exc}'
        ) from None

    bad_keys = [k for k in cfg if k not in defaults]

    if bad_keys:
        raise ValidationError(
            f"Deep check: node '{nodename}' declares unknown keys {bad_keys}"
        )
