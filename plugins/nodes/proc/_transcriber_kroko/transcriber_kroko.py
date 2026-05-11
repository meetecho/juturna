"""
TranscriberKroko

@author: Lorenzo Miniero
@email: lorenzo@meetecho.com

Transcribe audio packets using kroko-onnx (WIP)
"""
import typing

import json
import websocket

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import AudioPayload
from juturna.payloads import ObjectPayload
from juturna.payloads import Draft

class TranscriberKroko(Node[AudioPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(
        self,
        ws,
        **kwargs
    ):
        """
        Parameters
        ----------
        ws : str
            Kroko endpoint, including port.
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self.ws_uri = ws
        self.ws = None

    def configure(self):
        """Configure the node"""

    def warmup(self):
        """Warmup the node"""
        self.ws = websocket.create_connection(self.ws_uri)
        self.ws.settimeout(0.001)

    def set_on_config(self, prop: str, value: typing.Any):
        """Hot-swap node properties"""

    def start(self):
        """Start the node"""
        # after custom start code, invoke base node start
        super().start()

    def stop(self):
        """Stop the node"""
        # after custom stop code, invoke base node stop
        super().stop()

    def destroy(self):
        """Destroy the node"""
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                return

    def update(self, message: Message[AudioPayload]):
        """Receive data from upstream, transmit data downstream"""
        self.logger.info(f'received {message.version}')

        origin = message.creator

        self.logger.info('transcribing audio content')

        samples = message.payload.audio

        try:
            self.ws.send(
                samples.tobytes(),
                opcode=websocket.ABNF.OPCODE_BINARY
            )
        except Exception as e:
            self.log.error(f"Kroko send error: {e}")
            return

        while True:
            try:
                msg = self.ws.recv()
                if not msg:
                    return
                result = json.loads(msg)
                to_send = Message[ObjectPayload](
                    creator=self.name,
                    version=message.version,
                    payload=Draft(ObjectPayload),
                    timers_from=message,
                )
                to_send.meta['origin'] = origin
                to_send.payload['transcript'] = result
                self.transmit(to_send)
                self.logger.info(f'transmit: {to_send.version}')
            except websocket.WebSocketTimeoutException:
                return
            except Exception as e:
                self.log.error(f"Kroko recv error: {e}")
                return

    # uncomment next_batch to design custom synchronisation policy
    # def next_batch(sources: dict[str, list[Message]]) -> dict[str, list[int]]:
    #     ...
