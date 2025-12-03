"""
NotifierUDP

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com

Transmit message to a UDP socket.
"""

import socket
import json
import base64
import typing

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import ObjectPayload


class NotifierUDP(Node[ObjectPayload, None]):
    """Send data to a UDP endpoint, managing segmentation"""

    def __init__(
        self,
        endpoint: str,
        port: int,
        payload_size: int,
        max_sequence: int,
        max_chunks: int,
        encoding: str,
        encode_b64: bool,
        **kwargs,
    ):
        """
        Parameters
        ----------
        endpoint : str
            Address of the destination endpoint.
        port : int
            Port of the destination endpoint.
        payload_size : int
            Size of each payload (including header).
        max_sequence : int
            Maximum sequence number before reset.
        max_chunks : int
            Maximum fragment number before reset.
        encoding : str
            Data encoding.
        encode_b64 : bool
            Whether to encode data to base64.
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._address = [endpoint, port]
        self._payload_size = payload_size
        self._max_sequence = max_sequence
        self._max_chunks = max_chunks
        self._encoding = encoding
        self._encode_b64 = encode_b64

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._meta_overhead = len(
            json.dumps(
                {
                    'seq': self._max_sequence,
                    'frag': self._max_chunks - 1,
                    'tot': self._max_chunks - 1,
                    'data': '',
                }
            )
        )

        self._data_size = self._payload_size - self._meta_overhead

    def set_on_config(self, prop: str, value: typing.Any):
        """Change node configuration"""
        if prop == 'endpoint':
            self._address[0] = value
        elif prop == 'port':
            self._address[1] = value

    def update(self, message: Message[ObjectPayload]):
        """Receive a message, transmit a message"""
        chunks = self._prepare_chunks(message, message.version)

        for chunk in chunks:
            self._socket.sendto(chunk, tuple(self._address))

    def _prepare_chunks(self, message: Message, version: int) -> list[bytes]:
        chunks = list()
        json_bytes = message.to_json().encode(self._encoding)

        if self._encode_b64:
            json_bytes = base64.b64encode(json_bytes).decode('ascii')

        total_chunks = (
            len(json_bytes) + self._payload_size - 1
        ) // self._data_size

        for i in range(total_chunks):
            start_idx = i * self._data_size
            end_idx = min(start_idx + self._data_size, len(json_bytes))
            payload_chunk = json_bytes[start_idx:end_idx]

            chunk_obj = {
                'seq': version % self._max_sequence,
                'frag': i % self._max_chunks,
                'tot': total_chunks,
                'data': payload_chunk,
            }

            chunk_bytes = json.dumps(chunk_obj).encode(self._encoding)

            if len(chunk_bytes) > self._payload_size:
                raise ValueError(
                    f'chunk size {len(chunk_bytes)} '
                    'exceeds buffer size {self._payload_size}'
                )

            chunks.append(chunk_bytes)

        return chunks
