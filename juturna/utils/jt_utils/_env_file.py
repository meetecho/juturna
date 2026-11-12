import pathlib
import re


_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
_ESCAPES = {'n': '\n', 't': '\t', 'r': '\r', '"': '"', '\\': '\\'}


class EnvFileError(ValueError):
    """Raised when an environment file cannot be parsed."""


def read_env_file(path: str | pathlib.Path) -> dict[str, str]:
    """
    Read variables from an environment file, without touching the
    environment of the process.

    The file has one ``NAME=value`` per line. Empty lines and lines starting
    with ``#`` are skipped, and a leading ``export`` is accepted. A value can
    be:

    - bare: it ends at the end of the line, or at a ``#`` that follows a
      space, and the spaces around it are dropped;
    - in single quotes: taken as it is;
    - in double quotes: a backslash followed by ``n``, ``t``, ``r``, ``"``
      or another backslash is an escape.

    Values are not expanded (``$OTHER`` stays as written) and cannot span
    lines. When a name is repeated, the last value wins.

    Parameters
    ----------
    path : str | pathlib.Path
        The file to read.

    Returns
    -------
    dict[str, str]
        The variables of the file.

    Raises
    ------
    OSError
        If the file cannot be read.
    EnvFileError
        If a line cannot be parsed. The message has the line number, never
        its content, which may be a secret.

    """
    variables = dict()

    with open(path, encoding='utf-8') as f:
        for number, line in enumerate(f, start=1):
            try:
                parsed = _parse_line(line)
            except ValueError as error:
                raise EnvFileError(f'{path}, line {number}: {error}') from None

            if parsed is not None:
                variables[parsed[0]] = parsed[1]

    return variables


def _parse_line(line: str) -> tuple[str, str] | None:
    line = line.strip()

    if not line or line.startswith('#'):
        return None

    if line.startswith('export') and line[6:7].isspace():
        line = line[6:].lstrip()

    name, separator, value = line.partition('=')
    name = name.rstrip()

    if not separator:
        raise ValueError('expected NAME=value')

    if not _NAME.fullmatch(name):
        raise ValueError('invalid variable name')

    return name, _parse_value(value.lstrip())


def _parse_value(value: str) -> str:
    if value[:1] == "'":
        end = value.find("'", 1)

        if end < 0:
            raise ValueError('missing closing quote')

        _check_rest(value[end + 1 :])

        return value[1:end]

    if value[:1] == '"':
        return _parse_double_quoted(value)

    # a bare value: a comment starts at a # that follows a space
    comment = re.search(r'\s#', value)

    if comment:
        value = value[: comment.start()]

    return value.rstrip()


def _parse_double_quoted(value: str) -> str:
    chars = list()
    position = 1

    while position < len(value):
        char = value[position]

        if char == '"':
            _check_rest(value[position + 1 :])

            return ''.join(chars)

        if char == '\\' and value[position + 1 : position + 2] in _ESCAPES:
            chars.append(_ESCAPES[value[position + 1]])
            position += 2

            continue

        chars.append(char)
        position += 1

    raise ValueError('missing closing quote')


def _check_rest(rest: str):
    rest = rest.strip()

    if rest and not rest.startswith('#'):
        raise ValueError('unexpected text after the closing quote')
