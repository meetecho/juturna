import socket
import logging

from juturna.utils.net_utils import RTPDatagram


class RTPClient:
    """
    RTPClient is a class that represents a Real-time Transport Protocol (RTP)
    client. It is used to send and receive RTP packets over a network.
    """
    def __init__(self, host: str, port: int):
        """
        Parameters
        ----------
        host : str
            The host address of the RTP server.
        port : int
            The port number of the RTP server.
        """
        self.host = host
        self.port = port

        self._socket = None
        self._is_connected = False

    def __repr__(self):
        return f'<RTPClient [{self.host}]'

    def connect(self):
        """
        Connect to the RTP server by creating a UDP socket and binding it to
        the specified host and port.
        """
        if self._socket:
            return

        logging.info(f'local bind to {self.host}:{self.port}')

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((self.host, self.port))

        self._is_connected = True

    def disconnect(self):
        """
        Disconnect from the RTP server and clean up resources.
        """
        try:
            self._socket.close()
            self.send_terminate()
            self._socket = None
        except AttributeError:
            logging.info('socket not created')

        self._is_connected = False
        logging.info('local rtp client disconnected')

    def send_terminate(self):
        """
        Send a termination signal to the RTP server by sending a blank UDP
        packet. This is used to inform the server that the client is
        disconnecting.
        """
        blank_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        blank_socket.sendto('000000000000xxxx'.encode(),
                            (self.host, self.port))

    def rec(self, chunk_size: int = 1024) -> RTPDatagram:
        """
        Receive RTP packets from the server. This method blocks until a packet
        is received or an error occurs.

        Parameters
        ----------
        chunk_size : int
            The size of the buffer to receive data. Default is 1024 bytes.

        Returns
        -------
        RTPDatagram
            The received RTP datagram. If an error occurs, None is returned.
        """
        try:
            data = self._socket.recv(chunk_size)
            data = RTPDatagram(data)
        except OSError:
            data = None

        return data

    @property
    def connected(self):
        return self._is_connected
