import argparse
import json

import pytest

from juturna.cli.commands import validate
from juturna.cli.commands._validation_tools import Check
from juturna.cli.commands._validation_tools import ValidationError


_NODE_TYPE = 'contrib.jt_test.nodes.PassthroughIdentity'

_CHECKS = [
    'JSON well formed',
    'Configuration structure',
    'Nodes well formed',
    'Links well formed',
    'Valid transport',
    'Valid telemetry',
    'Node types and arguments',
    'DAG properties',
]


def _node(name: str, node_type: str = _NODE_TYPE, **fields) -> dict:
    return {'name': name, 'type': node_type, 'configuration': {}, **fields}


def _config(nodes=None, links=None, **pipeline) -> dict:
    return {
        'version': '3.0.0',
        'pipeline': {
            'name': 'validated',
            'id': 'validated',
            'folder': 'validated',
            'nodes': [_node('a'), _node('b')] if nodes is None else nodes,
            'links': [{'from': 'a', 'to': 'b'}] if links is None else links,
            **pipeline,
        },
    }


def _validate(tmp_path, config) -> tuple[int, dict]:
    config_path = tmp_path / 'config.json'
    report_path = tmp_path / 'report.json'

    if isinstance(config, str):
        config_path.write_text(config)
    else:
        config_path.write_text(json.dumps(config))

    args = argparse.Namespace(config=str(config_path), report=str(report_path))
    code = validate._execute(args)

    report = json.loads(report_path.read_text())

    return code, {c['name']: c for c in report['checks']} | {
        '_success': report['success'],
        '_dag': report['dag'],
    }


def test_valid_pipeline(tmp_path):
    code, report = _validate(tmp_path, _config())

    assert code == 0
    assert report['_success'] is True
    assert all(report[name]['success'] for name in _CHECKS)
    assert report['_dag']['edges'] == [['a', 'b']]


@pytest.mark.parametrize(
    'config, failing, error',
    [
        ('{"pipeline": ', 'JSON well formed', 'Cannot read JSON'),
        ({'version': '3.0.0'}, 'Configuration structure', "'pipeline'"),
        (
            {'pipeline': {'name': 'p', 'nodes': {}, 'links': []}},
            'Configuration structure',
            'nodes is not a list',
        ),
        (_config(nodes=['a']), 'Nodes well formed', 'not an object'),
        (
            _config(nodes=[{'name': 'a', 'type': _NODE_TYPE}], links=[]),
            'Nodes well formed',
            'configuration',
        ),
        (
            _config(nodes=[_node('a'), _node('a')], links=[]),
            'Nodes well formed',
            'duplicate node name',
        ),
        (
            _config(nodes=[_node('../a')], links=[]),
            'Nodes well formed',
            'invalid node name',
        ),
        (
            _config(links=[{'from': 'a', 'to': 'ghost'}]),
            'Links well formed',
            'has no node ghost',
        ),
        (
            _config(links=[{'from': 'a', 'to': 'b'}, {'from': 'a', 'to': 'b'}]),
            'Links well formed',
            'duplicate link',
        ),
        (_config(links=[{'from': 'a'}]), 'Links well formed', 'missing keys'),
        (_config(transport='pigeon'), 'Valid transport', 'pigeon'),
        (_config(telemetry='tele.csv'), 'Valid telemetry', 'telemetry'),
        (
            _config(nodes=[_node('a', 'totally.missing.Node')], links=[]),
            'Node types and arguments',
            'cannot resolve type',
        ),
        (
            _config(links=[{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'a'}]),
            'DAG properties',
            'cycle',
        ),
    ],
)
def test_invalid_pipeline_fails_with_its_check(tmp_path, config, failing, error):
    code, report = _validate(tmp_path, config)

    assert code == 1, 'Expected a non-zero exit code'
    assert report['_success'] is False
    assert report[failing]['success'] is False, f'{failing} did not fail'
    assert error in report[failing]['error']

    # what comes before the failing check passed
    for name in _CHECKS[: _CHECKS.index(failing)]:
        assert report[name]['success'] is not False, f'{name} failed too'


def test_checks_after_a_failure_are_skipped(tmp_path):
    code, report = _validate(tmp_path, {'version': '3.0.0'})

    assert code == 1

    for name in _CHECKS[2:]:
        assert report[name]['skipped'] is True, f'{name} was not skipped'


def test_warnings_do_not_fail_the_validation(tmp_path, monkeypatch):
    monkeypatch.delenv('NOT_SET_FOR_VALIDATE', raising=False)

    nodes = [
        _node('a', sync='nope'),
        _node(
            'b',
            configuration={'colour': 1, 'delay': '$JT_ENV_NOT_SET_FOR_VALIDATE'},
        ),
    ]
    code, report = _validate(tmp_path, _config(nodes=nodes))

    assert code == 0
    warnings = report['Node types and arguments']['warnings']

    assert any("unknown sync 'nope'" in w for w in warnings), warnings
    assert any("unknown configuration keys ['colour']" in w for w in warnings)
    assert any('NOT_SET_FOR_VALIDATE' in w for w in warnings), warnings


def test_disconnected_nodes_are_a_warning(tmp_path):
    nodes = [_node('a'), _node('b'), _node('c')]
    code, report = _validate(tmp_path, _config(nodes=nodes))

    assert code == 0
    assert any('c' in w for w in report['DAG properties']['warnings'])


def test_failing_check_is_not_reported_as_passed():
    def _fail():
        raise ValidationError('broken')

    check = Check('fails', _fail)

    assert check() is False
    assert check.ok is False
    assert check.error == 'broken'


def test_unexpected_exception_is_a_failed_check():
    def _crash():
        raise KeyError('x')

    check = Check('crashes', _crash)

    assert check() is False
    assert check.error.startswith('KeyError')
