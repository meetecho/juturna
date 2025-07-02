import socket
import json
import base64
import typing

from juturna.components import BaseNode
from juturna.components import Message


class NotifierUDP(BaseNode):
    def __init__(self,
                 endpoint: str,
                 port: int,
                 payload_size: int,
                 max_chunks: int,
                 encoding: str,
                 encode_b64: bool):
        super().__init__('sink')

        self._address = [endpoint, port]
        self._payload_size = payload_size
        self._max_chunks = max_chunks
        self._encoding = encoding
        self._encode_b64 = encode_b64

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._meta_overhead = len(json.dumps({
            'seq': self._max_chunks -1,
            'total': self._max_chunks -1,
            'data': ''
        }))

    def configure(self):
        ...

    def warmup(self):
        ...

    def set_on_config(self, property: str, value: typing.Any):
        if property == 'endpoint':
            self._address[0] = value
        elif property == 'port':
            self._address[1] = value

    def destroy(self):
        ...

    def update(self, message: Message):
        chunks = self.prepare_chunks(message.payload)

        for chunk in chunks:
            self._socket.sendto(chunk, tuple(self._address))

    def prepare_chunks(self, data: dict) -> typing.List[bytes]:
        chunks = list()
        json_bytes = json.dumps(data).encode(self._encoding)

        if self._encode_b64:
            json_bytes = base64.b64encode(json_bytes).decode('ascii')

        total_chunks = (len(json_bytes) + self._payload_size - 1) // \
            self._payload_size

        for i in range(total_chunks):
            start_idx = i * self._payload_size
            end_idx = min(start_idx + self._payload_size, len(json_bytes))
            payload_chunk = json_bytes[start_idx:end_idx]

            chunk_obj = {
                'seq': i % self._max_chunks,
                'total': total_chunks,
                'data': payload_chunk
            }

            chunk_bytes = json.dumps(chunk_obj).encode(self._encoding)

            if len(chunk_bytes) > self._payload_size:
                raise ValueError(f'chunk size {len(chunk_bytes)} exceeds buffer size {self._payload_size}')

            chunks.append(chunk_bytes)

        return chunks