import socket
import logging

from juturna.utils.net_utils import RTPDatagram


class RTPClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

        self._socket = None
        self._is_connected = False

    def __repr__(self):
        return f'<RTPClient [{self.host}]'

    def connect(self):
        if self._socket:
            return

        logging.info(f'local bind to {self.host}:{self.port}')

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((self.host, self.port))

        self._is_connected = True

    def disconnect(self):
        try:
            self._socket.close()
            self.send_terminate()
            self._socket = None
        except AttributeError:
            logging.info('socket not created')

        self._is_connected = False
        logging.info('local rtp client disconnected')

    def send_terminate(self):
        blank_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        blank_socket.sendto('000000000000xxxx'.encode(),
                            (self.host, self.port))

    def rec(self, chunk_size: int = 1024):
        try:
            data = self._socket.recv(chunk_size)
            data = RTPDatagram(data)
        except OSError:
            data = None

        return data

    @property
    def connected(self):
        return self._is_connected
