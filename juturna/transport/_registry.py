from juturna.transport._base import TransportBackend
from juturna.transport._threading import ThreadingTransport
from juturna.transport._browser import BrowserTransport


_TRANSPORTS: dict[str, type[TransportBackend]] = {
    'threading': ThreadingTransport,
    'browser': BrowserTransport,
}

_DEFAULT_TRANSPORT = 'threading'


def get_transport(name: str | None = None) -> TransportBackend:
    """
    Resolve a transport backend by name.

    Parameters
    ----------
    name : str | None
        The name of the transport backend, as registered in `_TRANSPORTS`.
        Defaults to the threading backend if not provided.

    Returns
    -------
    TransportBackend
        A new instance of the requested backend.

    Raises
    ------
    ValueError
        If `name` does not match any registered backend.

    """
    name = name or _DEFAULT_TRANSPORT

    if name not in _TRANSPORTS:
        raise ValueError(
            f'unknown transport backend: {name!r}, '
            f'available: {list(_TRANSPORTS)}'
        )

    return _TRANSPORTS[name]()
