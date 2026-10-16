import re


# a single path component: no separators, no leading dot (so no "." or "..")
# and no leading dash, short enough to leave room for suffixes
_SAFE_NAME = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}')


def check_name(name, kind: str) -> str:
    """
    Check that a name taken from a configuration can be used as a file or
    folder name, so that joining it to a base folder cannot escape it.

    Parameters
    ----------
    name : Any
        The name to check.
    kind : str
        What the name identifies (``pipeline``, ``node``, ...), used in the
        error message.

    Returns
    -------
    str
        The name, unchanged.

    Raises
    ------
    ValueError
        If the name is not a string of up to 128 letters, digits, ``_``,
        ``-`` and ``.``, starting with a letter, a digit or ``_``.

    """
    if not isinstance(name, str) or not _SAFE_NAME.fullmatch(name):
        raise ValueError(
            f'invalid {kind} name {name!r}: use up to 128 letters, digits, '
            '"_", "-" and ".", starting with a letter, a digit or "_"'
        )

    return name
