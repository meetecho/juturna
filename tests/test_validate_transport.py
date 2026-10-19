import pytest

from juturna.cli.commands._validation_tools import ValidationError
from juturna.cli.commands.validate import _check_transport


@pytest.mark.parametrize(
    'pipeline',
    [
        {},
        {'transport': None},
        {'transport': 'threading'},
        {'transport': 'browser'},
        {'transport': {'name': 'browser', 'queue_capacity': 4}},
    ],
)
def test_valid_transports(pipeline):
    _check_transport(pipeline)


@pytest.mark.parametrize(
    'pipeline',
    [
        {'transport': 'nope'},
        {'transport': {'name': 'nope'}},
    ],
)
def test_unknown_transport_is_a_validation_error(pipeline):
    with pytest.raises(ValidationError, match='nope'):
        _check_transport(pipeline)


@pytest.mark.parametrize('transport', [['browser'], 5, {'name': ['browser']}])
def test_transport_of_the_wrong_type_is_a_validation_error(transport):
    with pytest.raises(ValidationError, match='transport'):
        _check_transport({'transport': transport})


def test_transport_with_an_unknown_option_is_a_validation_error():
    with pytest.raises(ValidationError, match='invalid options'):
        _check_transport({'transport': {'name': 'browser', 'colour': 1}})
