import json

from websockets.sync.server import serve

from juturna.components import BaseNode
from juturna.components import Message


class JsonWebsocket(BaseNode):
    def __init__(self, rcx_host: str):
        super().__init__('source')

        self._rcx_host = rcx_host

        self._sent = 0

    def warmup(self):
        ...
