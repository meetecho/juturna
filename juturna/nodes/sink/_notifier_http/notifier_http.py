"""
NotifierHTTP

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com

Transmit message to a HTTP endpoint.
"""

import requests

from juturna.components import Message
from juturna.components import Node

from juturna.meta import JUTURNA_DRAIN_TIMEOUT
from juturna.meta import JUTURNA_MAX_QUEUE_SIZE
from juturna.meta import JUTURNA_THREAD_JOIN_TIMEOUT
from juturna.payloads import ObjectPayload
from juturna.transport import Empty
from juturna.transport import Queue
from juturna.transport import Signal
from juturna.transport import WorkerHandle


class NotifierHTTP(Node[ObjectPayload, None]):
    """Send data to a HTTP endpoint"""

    _CNT_CB = {
        'application/json': lambda m: m.to_dict(),
        'text/plain': lambda m: m.to_json(),
    }

    def __init__(
        self, endpoint: str, timeout: int, content_type: str, **kwargs
    ):
        """
        Parameters
        ----------
        endpoint : str
            Destination endpoint, including the port.
        timeout : int
            Transmission timeout.
        content_type : str
            Transmission data content type (this node supports, for now,
            application/json and text/plain data).
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._endpoint = endpoint
        self._timeout = timeout
        self._content_type = content_type

        self._send_queue: Queue = self._transport.new_queue(
            maxsize=JUTURNA_MAX_QUEUE_SIZE
        )
        self._stop_sender_event: Signal = self._transport.new_signal()
        self._sender_thread: WorkerHandle | None = None

    @property
    def configuration(self) -> dict:
        """Fetch node configuration"""
        base_config = super().configuration
        base_config['endpoint'] = self._endpoint

        return base_config

    def warmup(self):
        """Warmup the node"""
        self.logger.info(f'[{self.name}] set to endpoint {self._endpoint}')

        self._sender_thread = self._transport.spawn(
            target=self._sender_loop,
            name=f'{self.name}_sender',
            daemon=True,
        )

    def start(self):
        """Start the sender worker"""
        self._sender_thread.start()

        super().start()

    def stop(self):
        """Stop the node, then drain and stop the sender worker"""
        super().stop()

        self._stop_sender_event.set()

        if self._sender_thread:
            self._sender_thread.join(timeout=JUTURNA_DRAIN_TIMEOUT)

            if self._sender_thread.is_alive():
                self.logger.warning(
                    f'sender worker still draining after '
                    f'{JUTURNA_DRAIN_TIMEOUT}s, '
                    f'{self._send_queue.qsize()} message(s) may be dropped'
                )

    def set_on_config(self, prop: str, value: str):
        """Change the node configuration"""
        if prop == 'endpoint':
            self.logger.info(f'updating endpoint to {value}')

            self._endpoint = value

    def update(self, message: Message[ObjectPayload], **kwargs):
        """Receive a message, transmit a message"""
        to_send = Message[ObjectPayload](
            creator=message.creator,
            version=message.version,
            timers_from=message,
            payload=message.payload,
        )

        to_send.meta['pipe_id'] = self.pipe_id
        to_send = NotifierHTTP._CNT_CB[self._content_type](to_send)

        self._send_queue.put(to_send)

    def _sender_loop(self):
        """Drain the send queue and forward each entry to the endpoint"""
        while True:
            try:
                message_cnt = self._send_queue.get(
                    timeout=JUTURNA_THREAD_JOIN_TIMEOUT
                )
            except Empty:
                if self._stop_sender_event.is_set():
                    return

                continue

            self._send_chunk(message_cnt)

    def _send_chunk(self, message_cnt):
        try:
            headers = {'Content-Type': self._content_type}
            response = requests.post(
                self._endpoint,
                json=message_cnt,
                headers=headers,
                timeout=self._timeout,
            )

            self.logger.info(f'message sent: {response.status_code}')
        except Exception as e:
            self.logger.info(e)
