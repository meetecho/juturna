import pytest

from juturna.utils.jt_utils import EnvFileError
from juturna.utils.jt_utils import read_env_file


def _read(tmp_path, content: str) -> dict:
    path = tmp_path / 'pipelines.env'
    path.write_text(content)

    return read_env_file(path)


def test_env_file_reads_names_and_values(tmp_path):
    variables = _read(
        tmp_path,
        '# a comment\n'
        '\n'
        'PLAIN=value\n'
        'SPACED = around the sign  \n'
        'export EXPORTED=yes\n'
        'EMPTY=\n'
        'URL=http://host:80/path?a=b#fragment\n'
        'COMMENTED=value # not part of it\n',
    )

    assert variables == {
        'PLAIN': 'value',
        'SPACED': 'around the sign',
        'EXPORTED': 'yes',
        'EMPTY': '',
        'URL': 'http://host:80/path?a=b#fragment',
        'COMMENTED': 'value',
    }


def test_env_file_quotes(tmp_path):
    variables = _read(
        tmp_path,
        "SINGLE='as # it $IS\\n'\n"
        'DOUBLE="a # \\"b\\"\\n\\\\" # comment\n'
        'NOT_EXPANDED="$PLAIN ${PLAIN}"\n',
    )

    assert variables == {
        'SINGLE': 'as # it $IS\\n',
        'DOUBLE': 'a # "b"\n\\',
        'NOT_EXPANDED': '$PLAIN ${PLAIN}',
    }


def test_env_file_last_value_wins(tmp_path):
    assert _read(tmp_path, 'A=1\nA=2\n') == {'A': '2'}


@pytest.mark.parametrize(
    'line',
    [
        'no_equal_sign_s3cret',
        '1NAME=s3cret',
        'NA-ME=s3cret',
        '=s3cret',
        "OPEN='s3cret",
        'OPEN="s3cret',
        "TRAILING='s3cret' more",
        'TRAILING="s3cret" more',
    ],
)
def test_env_file_error_names_the_line_not_its_content(tmp_path, line):
    with pytest.raises(EnvFileError) as error:
        _read(tmp_path, f'GOOD=1\n{line}\n')

    assert 'line 2' in str(error.value)
    assert 's3cret' not in str(error.value)
    # nothing chained that would print the line in a traceback
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__


def test_env_file_does_not_touch_the_environment(tmp_path, monkeypatch):
    import os

    monkeypatch.delenv('JT_FILE_ONLY', raising=False)
    _read(tmp_path, 'JT_FILE_ONLY=1\n')

    assert 'JT_FILE_ONLY' not in os.environ


def test_env_file_missing(tmp_path):
    with pytest.raises(OSError):
        read_env_file(tmp_path / 'missing.env')
