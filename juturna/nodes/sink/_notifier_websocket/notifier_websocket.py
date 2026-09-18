"""
NotifierWebsocket

@ Author: Antonio Bevilacqua, Paolo Saviano
@ Email: abevilacqua@meetecho.com, psaviano@meetecho.com

Transmit message to a websocket socket.

Keeps a single connection open across messages instead of one
connect()/close() per message
"""

import time

from websockets.sync.client import ClientConnection
from websockets.sync.client import connect

from juturna.components import Message
from juturna.components import Node

from juturna.payloads import BasePayload
from juturna.payloads import ObjectPayload


class NotifierWebsocket(Node[BasePayload, None]):
    """Transmit data to a websocket endpoint"""

    def __init__(
        self,
        endpoint: str,
        topic_key: str | None = None,
        max_retries: int = 3,
        retry_backoff_s: float = 0.3,
        **kwargs,
    ):
        """
        Parameters
        ----------
        endpoint : str
            Destination endpoint, including port.
        max_retries : int
            Attempts to (re)connect and send a message before giving
            it up as failed. A fresh handshake is attempted on every
            retry, since a failed send generally means the connection
            itself is no longer usable.
        retry_backoff_s : float
            Delay between retries, in seconds.
        topic_key : str, optional
            If set, and the incoming payload is an ObjectPayload that
            doesn't already have a 'topic' key, stamp one on using the
            value found under this key name - checked first on the
            payload itself, then falling back to
            meta['source_meta'][topic_key].
            Left unset, the payload is forwarded exactly
            as received.
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._endpoint = endpoint
        self._topic_key = topic_key
        self._max_retries = max_retries
        self._retry_backoff_s = retry_backoff_s

        self._ws: ClientConnection | None = None

    def warmup(self):
        """Warmup the node"""
        self.logger.info(f'[{self.name}] set to endpoint {self._endpoint}')

    def _stamp_topic(self, message: Message[BasePayload]):
        payload = message.payload
        if (
            self._topic_key is None
            or not isinstance(payload, ObjectPayload)
            or 'topic' in payload
        ):
            return payload

        topic = payload.get(self._topic_key)
        if topic is None:
            topic = message.meta.get('source_meta', {}).get(self._topic_key)
        if topic is None:
            return payload

        return ObjectPayload(**dict(payload), topic=topic)

    def update(self, message: Message[BasePayload], **kwargs):
        """Receive a message, transmit a message"""
        meta = dict(message.meta)
        to_send = Message[BasePayload](
            creator=message.creator,
            version=message.version,
            payload=self._stamp_topic(message),
        )

        meta['session_id'] = self.pipe_id
        to_send.meta = meta

        self._send_message(to_send)

    def _send_message(self, message: Message[BasePayload]):
        """Send over the persistent connection, reconnecting on failure."""
        message_json = message.to_json()

        for attempt in range(1, self._max_retries + 1):
            try:
                if self._ws is None:
                    self._ws = connect(self._endpoint)

                self._ws.send(message_json)

                return
            except Exception as e:
                self.logger.warning(
                    f'[{self.name}] send attempt {attempt}/'
                    f'{self._max_retries} failed: {e}'
                )

                if self._ws is not None:
                    self._ws.close()
                    self._ws = None

                if attempt < self._max_retries:
                    time.sleep(self._retry_backoff_s)

        raise RuntimeError(
            f'[{self.name}] giving up on message after '
            f'{self._max_retries} attempts'
        )

    def destroy(self):
        """Destroy the node"""
        if self._ws is not None:
            self._ws.close()
            self._ws = None
