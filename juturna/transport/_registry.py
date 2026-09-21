import inspect

from juturna.transport._base import TransportBackend
from juturna.transport._threading import ThreadingTransport
from juturna.transport._browser import BrowserTransport


_TRANSPORTS: dict[str, type[TransportBackend]] = {
    'threading': ThreadingTransport,
    'browser': BrowserTransport,
}

_DEFAULT_TRANSPORT = 'threading'


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
    options = dict(spec) if isinstance(spec, dict) else dict()
    name = options.pop('name', None) if options else spec
    name = name or _DEFAULT_TRANSPORT

    if name not in _TRANSPORTS:
        raise ValueError(
            f'unknown transport backend: {name!r}, '
            f'available: {list(_TRANSPORTS)}'
        )

    try:
        inspect.signature(_TRANSPORTS[name]).bind(**options)
    except TypeError as exc:
        raise ValueError(
            f'invalid options for the {name!r} transport: {exc}'
        ) from exc

    return _TRANSPORTS[name](**options)
