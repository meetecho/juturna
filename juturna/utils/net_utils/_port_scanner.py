import socket


def get_available_port() -> int:
    """
    Returns an available port number.
    This function creates a socket, binds it to an available port, and then
    closes the socket.

    Returns
    -------
    int
        An available port number.

    """
    s = socket.socket()
    s.bind(('', 0))

    port = s.getsockname()[1]
    s.close()

    return port
