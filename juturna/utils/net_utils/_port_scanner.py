import socket


def get_available_port() -> int:
    s = socket.socket()
    s.bind(('', 0))

    port = s.getsockname()[1]
    s.close()

    return port