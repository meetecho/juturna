"""
Pipeline validation module

Validate a pipeline from the CLI. Provide the pipeline configuration, and the
module will analyse its content, checking if the pipeline is properly configured
and all its components are available.

"""

import json
import os
import pathlib
import typing

from juturna.cli.commands import _common_pipe_parser
from juturna.cli.commands._validation_tools import Check
from juturna.cli.commands._validation_tools import ValidationPipe
from juturna.cli.commands._validation_tools import ValidationError
from juturna.cli.commands._validation_tools import DAG
from juturna.cli.commands._validation_tools import warn

from juturna.components._node_builder import _builder
from juturna.components._pipeline import check_links
from juturna.meta import JUTURNA_ENV_VAR_PREFIX
from juturna.telemetry import check_pipeline_telemetry
from juturna.transport import get_transport
from juturna.utils import jt_utils


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


def _execute(args) -> int:
    validation_pipe = ValidationPipe()

    # filled by the checks as they pass, so that each one can rely on what
    # the previous ones verified
    state: dict[str, typing.Any] = {'path': pathlib.Path(args.config)}

    checks = [
        Check('JSON well formed', _check_json),
        Check(
            'Configuration structure',
            _check_config_structure,
            requires=('JSON well formed',),
        ),
        Check(
            'Nodes well formed',
            lambda s: _check_nodes_well_formed(s['pipeline']['nodes']),
            requires=('Configuration structure',),
        ),
        Check(
            'Links well formed',
            lambda s: _check_links_well_formed(s['pipeline']),
            requires=('Nodes well formed',),
        ),
        Check(
            'Valid transport',
            lambda s: _check_transport(s['pipeline']),
            requires=('Configuration structure',),
        ),
        Check(
            'Valid telemetry',
            lambda s: _check_telemetry(s['pipeline']),
            requires=('Configuration structure',),
        ),
        Check(
            'Node types and arguments',
            lambda s: _check_node_types(s['pipeline']['nodes']),
            requires=('Nodes well formed',),
        ),
        Check('DAG properties', _check_dag, requires=('Links well formed',)),
    ]

    for check in checks:
        validation_pipe.add_check(check)

    validation_pipe.run_checks(state)
    validation_pipe.dag = state.get('dag')

    print('valid' if validation_pipe.ok else 'invalid')

    if args.report:
        with open(args.report, 'w') as f:
            f.write(validation_pipe.to_json())

    return 0 if validation_pipe.ok else 1


def _check_json(state: dict) -> None:
    state['data'] = _load_pipeline(state['path'])


def _check_config_structure(state: dict) -> None:
    _check_structure(state['data'])

    state['pipeline'] = state['data']['pipeline']


def _load_pipeline(cfg_path: pathlib.Path) -> dict[str, typing.Any]:
    try:
        with open(cfg_path) as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f'Cannot read JSON: {exc}') from None


def _check_transport(pipeline: dict) -> None:
    req_transport = pipeline.get('transport')

    if req_transport is None:
        return

    try:
        get_transport(req_transport)
    except ValueError as exc:
        raise ValidationError(f'Invalid transport: {exc}') from exc


def _check_telemetry(pipeline: dict) -> None:
    if pipeline.get('telemetry') is None:
        return

    try:
        check_pipeline_telemetry(pipeline)
    except ValueError as exc:
        raise ValidationError(
            f'Invalid telemetry configuration: {exc}'
        ) from exc


def _check_structure(data: typing.Any) -> None:
    if not isinstance(data, dict) or 'pipeline' not in data:
        raise ValidationError("Top-level key 'pipeline' missing")

    pl = data['pipeline']

    if not isinstance(pl, dict):
        raise ValidationError('pipeline is not an object')

    if not isinstance(pl.get('name'), str):
        raise ValidationError('pipeline.name missing')

    for key in ('nodes', 'links'):
        if key not in pl:
            raise ValidationError(f'pipeline.{key} missing')

        if not isinstance(pl[key], list):
            raise ValidationError(f'pipeline.{key} is not a list')


def _check_nodes_well_formed(nodes: list[typing.Any]) -> None:
    names = set()

    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValidationError(f'nodes[{idx}] is not an object')

        missing = {'name', 'type', 'configuration'} - node.keys()

        if missing:
            raise ValidationError(
                f'nodes[{idx}] missing keys: {sorted(missing)}'
            )

        if not isinstance(node['type'], str):
            raise ValidationError(f'nodes[{idx}].type is not a string')

        if not isinstance(node['configuration'], dict):
            raise ValidationError(
                f'nodes[{idx}].configuration is not an object'
            )

        # the name becomes the node folder, as in Pipeline.warmup()
        try:
            jt_utils.check_name(node['name'], 'node')
        except ValueError as exc:
            raise ValidationError(f'nodes[{idx}]: {exc}') from None

        if node['name'] in names:
            raise ValidationError(f'duplicate node name {node["name"]!r}')

        names.add(node['name'])


def _check_links_well_formed(pipeline: dict) -> None:
    links = pipeline['links']

    for idx, link in enumerate(links):
        if not isinstance(link, dict):
            raise ValidationError(f'links[{idx}] is not an object')

        missing = {'from', 'to'} - link.keys()

        if missing:
            raise ValidationError(
                f'links[{idx}] missing keys: {sorted(missing)}'
            )

    # the same check warmup() runs
    try:
        check_links(pipeline['name'], pipeline['nodes'], links)
    except ValueError as exc:
        raise ValidationError(str(exc)) from None


def _check_node_types(nodes: list[dict]) -> None:
    """
    Resolve every node type as the builder does, without building the node,
    and compare the configuration with the arguments the node accepts.
    """
    errors = list()

    for node in nodes:
        name = node['name']

        try:
            _, default_config = _builder._resolve_node(node['type'])
            arguments = default_config['arguments']
        except Exception as exc:
            errors.append(
                f'node {name}: cannot resolve type {node["type"]!r} '
                f'({type(exc).__name__}: {exc})'
            )

            continue

        # the builder drops these silently
        if unknown := sorted(node['configuration'].keys() - arguments.keys()):
            warn(f'node {name}: unknown configuration keys {unknown}')

        # synchronisers were removed: nodes now keep pending messages in
        # their state, and the key is ignored
        if 'sync' in node:
            warn(f'node {name}: sync is not supported anymore, ignored')

        for key, value in node['configuration'].items():
            if not (
                key in arguments
                and isinstance(value, str)
                and value.startswith(JUTURNA_ENV_VAR_PREFIX)
            ):
                continue

            var_name = value[len(JUTURNA_ENV_VAR_PREFIX) :]

            # only known when the pipeline is launched, maybe elsewhere
            if var_name not in os.environ:
                warn(
                    f'node {name}: {key} reads {var_name}, which is not set '
                    'here'
                )

    if errors:
        raise ValidationError('; '.join(errors))


def _check_dag(state: dict) -> None:
    pipeline = state['pipeline']
    dag = DAG()

    for n in pipeline['nodes']:
        dag.add_node(n['name'])

    for link in pipeline['links']:
        dag.add_edge(link['from'], link['to'])

    state['dag'] = dag

    _check_dag_properties(dag)


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
