import inspect

from juturna.transport._base import TransportBackend
from juturna.transport.threads import ThreadingTransport
from juturna.transport.browser import BrowserTransport


_TRANSPORTS: dict[str, type[TransportBackend]] = {
    'threading': ThreadingTransport,
    'browser': BrowserTransport,
}

_DEFAULT_TRANSPORT = 'threading'


def _split_spec(spec: str | dict | None) -> tuple[str, dict]:
    if isinstance(spec, dict):
        options = dict(spec)
        name = options.pop('name', None)
    elif spec is None or isinstance(spec, str):
        options, name = dict(), spec
    else:
        raise ValueError(
            f'transport must be a name or a dict, got {type(spec).__name__}'
        )

    if name is not None and not isinstance(name, str):
        raise ValueError(f'transport name must be a string, got {name!r}')

    return name or _DEFAULT_TRANSPORT, options


def get_transport(spec: str | dict | None = None) -> TransportBackend:
    """
    Resolve a transport backend from its configuration.

    Parameters
    ----------
    spec : str | dict | None
        Either the name of the backend, as registered in `_TRANSPORTS`, or a
        dictionary with its ``name`` and the options of the backend, that are
        passed to its constructor, like
        ``{'name': 'browser', 'max_payload_bytes': 4000000}``. Defaults to the
        threading backend if not provided.

    Returns
    -------
    TransportBackend
        A new instance of the requested backend.

    Raises
    ------
    ValueError
        If the name does not match any registered backend, or the backend
        does not accept one of the options.

    """
    name, options = _split_spec(spec)
    if name not in _TRANSPORTS:
        raise ValueError(
            f'unknown transport backend: {name!r}, '
            f'available: {list(_TRANSPORTS)}'
        )

    transport = _TRANSPORTS[name]

    try:
        inspect.signature(transport).bind(**options)
    except TypeError as exc:
        raise ValueError(
            f'invalid options for the {name!r} transport: {exc}'
        ) from exc

    return transport(**options)
