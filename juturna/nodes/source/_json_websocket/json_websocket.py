"""
JsonWebsocket

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com

Expose a websocket server and fetch input data from it.
"""

import json

from websockets.sync.server import serve

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import BytesPayload
from juturna.payloads import ObjectPayload
from juturna.payloads import Draft
from juturna.transport import WorkerHandle


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

        self._thread: WorkerHandle | None = None
        self._server = None

    def warmup(self):
        """Prepare node for execution"""
        self._server = serve(self._ws_handler, self._rtx_host, self._rtx_port)
        self._thread = self._transport.spawn(
            target=self._server.serve_forever,
            name=f'{self.name}_ws',
            daemon=True,
        )

        self.logger.info('ws server created')

    def start(self):
        """Start server thread"""
        self._thread.start()

        super().start()

    def stop(self):  # noqa: D102
        super().stop()

        if self._server:
            self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=2)

    def update(self, message: Message[BytesPayload], **kwargs):  # noqa: D102
        self.logger.info(f'ws server message received: {message.payload.cnt}')

        try:
            json_content = json.loads(message.payload.cnt.decode())
        except Exception:
            self.logger.warning('bad JSON, skipped')

            return

        state = kwargs.get('state')
        _sent = state.get('sent', 0)

        to_send = Message[ObjectPayload](
            creator=self.name, version=_sent, payload=Draft(ObjectPayload)
        )

        for k, v in json_content.items():
            to_send.payload[k] = v

        self.logger.info('ws source transmitting...')
        self.transmit(to_send)

        state['sent'] = _sent + 1

    def _ws_handler(self, websocket):
        try:
            for raw in websocket:
                cnt = raw.encode() if isinstance(raw, str) else raw
                payload = BytesPayload(cnt=cnt)

                msg = Message[BytesPayload](creator=self.name, payload=payload)

                self.put(msg)
        except Exception as exc:
            self.logger.warning('ws handler died: %s', exc)
