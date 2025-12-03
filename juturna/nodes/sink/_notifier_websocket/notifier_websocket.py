"""
NotifierWebsocket

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com

Transmit message to a websocket socket.
"""

import json
import threading

from websockets.sync.client import connect

from juturna.components import Message
from juturna.components import Node

from juturna.payloads import ObjectPayload


class NotifierWebsocket(Node[ObjectPayload, None]):
    """Transmit data to a websocket endpoint"""

    def __init__(self, endpoint: str, **kwargs):
        """
        Parameters
        ----------
        endpoint : str
            Destination endpoint, including port.
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._endpoint = endpoint

        self._sent = 0
        self._t = None

    def warmup(self):
        """Warmup the node"""
        self.logger.info(f'[{self.name}] set to endpoint {self._endpoint}')

    def update(self, message: Message[ObjectPayload]):
        """Receive a message, transmit a message"""
        message = message.to_dict()
        message['session_id'] = self.pipe_id

        self._t = threading.Thread(
            name='_post_transcript',
            target=self._send_message,
            args=(message,),
            daemon=True,
        )

        self._t.start()

        self._sent += 1

    def _send_message(self, message_dict: dict):
        with connect(self._endpoint) as ws:
            try:
                ws.send(json.dumps(message_dict))
            except Exception as e:
                self.logger.warning(e)

    def destroy(self):
        """Destroy the node"""
        if self._t:
            self._t.join()
        ...
