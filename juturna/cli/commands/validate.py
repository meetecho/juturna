"""
Pipeline validation module

Validate a pipeline from the CLI. Provide the pipeline configuration, and the
module will analyse its content, checking if the pipeline is properly configured
and all its components are available.

"""

import json
import pathlib
import typing

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
        '--report',
        '-r',
        metavar='FILE',
        help='save json report of the validation test',
    )


def _execute(args):
    validation_pipe = ValidationPipe()

    cfg_path = pathlib.Path(args.config)

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
    required = {'name', 'type'}

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


def _check_dag_properties(dag: DAG) -> None:
    """No cycles, and no node disconnected from the rest of the pipeline."""
    if dag.has_cycle():
        raise ValidationError('Pipeline links contain a cycle → not a DAG')

    in_degree = dag.in_degree()
    out_degree = dag.out_degree()

    if len(in_degree) < 2:
        return

    disconnected = [
        n for n in in_degree if in_degree[n] == 0 and out_degree[n] == 0
    ]

    if disconnected:
        warn(f'Nodes with no input nor output links: {disconnected}')
