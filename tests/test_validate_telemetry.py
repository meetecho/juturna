import pytest

from juturna.cli.commands._validation_tools import ValidationError
from juturna.cli.commands.validate import _check_telemetry


def test_no_telemetry_is_valid():
    _check_telemetry({'nodes': [], 'links': []})


def test_null_telemetry_is_valid():
    _check_telemetry({'telemetry': None})


def test_valid_pairs():
    _check_telemetry({'telemetry': {'name': 'memory'}})
    _check_telemetry(
        {'transport': 'threading', 'telemetry': {'name': 'csv', 'target': 'x.csv'}}
    )
    _check_telemetry({'transport': 'browser', 'telemetry': {'name': 'browser'}})


@pytest.mark.parametrize(
    'pipeline',
    [
        {'telemetry': 'tele.csv'},
        {'telemetry': {'name': 'nope'}},
        {'telemetry': {'name': 'csv'}},
        {'transport': 'browser', 'telemetry': {'name': 'csv', 'target': 'x.csv'}},
        {'transport': 'threading', 'telemetry': {'name': 'browser'}},
        {'transport': 'nope', 'telemetry': {'name': 'memory'}},
        {'telemetry': {'name': 'csv', 'target': 5}},
        {'telemetry': {'name': 'csv', 'target': 'x.csv', 'max_pending': 0}},
        {'telemetry': {'name': 'memory', 'max_records': 0}},
        {'telemetry': {'name': 'memory', 'max_records': '5'}},
    ],
)
def test_invalid_pairs(pipeline):
    with pytest.raises(ValidationError):
        _check_telemetry(pipeline)
