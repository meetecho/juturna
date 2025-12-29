"""
JsonWebsocket

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com

Expose a websocket server and fetch input data from it.
"""

import json
import queue
import threading

from websockets.sync.server import serve

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import BytesPayload
from juturna.payloads import ObjectPayload
from juturna.payloads import Draft


class JsonWebsocket(Node[BytesPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(self, rtx_host: str, rtx_port: int, **kwargs):
        """
        Parameters
        ----------
        rtx_host : str
            Websocket server host.
        rtx_port : int
            Websocket server port.
        kwargs : dict
            Supernode args.

        """
        super().__init__(**kwargs)

        self._rtx_host = rtx_host
        self._rtx_port = rtx_port

        self._sent = 0
        self._queue: queue.Queue[Message[ObjectPayload]] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._server = None

    def warmup(self):
        """Prepare node for execution"""
        self._server = serve(self._ws_handler, self._rtx_host, self._rtx_port)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name=f'{self.name}_ws',
        )

        self.logger.info('ws server created')

    def start(self):
        """Start server thread and set source"""
        self.set_source(self._queue.get)
        self._thread.start()

        super().start()

    def stop(self):  # noqa: D102
        if self._server:
            self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=2)

    def update(self, message: Message[BytesPayload]):  # noqa: D102
        self.logger.info(f'ws server message received: {message.payload.cnt}')

        try:
            json_content = json.loads(message.payload.cnt.decode())
        except Exception:
            self.logger.warning('bad JSON, skipped')

            return

        to_send = Message[ObjectPayload](
            creator=self.name, version=self._sent, payload=Draft(ObjectPayload)
        )

        for k, v in json_content.items():
            to_send.payload[k] = v

        self.logger.info('ws source transmitting...')
        self.transmit(to_send)
        self._sent += 1

    def _ws_handler(self, websocket):
        try:
            for raw in websocket:
                payload = BytesPayload(cnt=raw)

                msg = Message[ObjectPayload](
                    creator=self.name, version=self._sent, payload=payload
                )

                self._queue.put(msg)
        except Exception as exc:
            self.logger.warning('ws handler died: %s', exc)
