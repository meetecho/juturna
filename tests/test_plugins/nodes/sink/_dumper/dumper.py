"""
Dumper

@author: Paolo Saviano
@email: psaviano@meetecho.com
@created_at: 2026-03-15 10:30:00

Test sink node. Dump received messages.
"""

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import BasePayload


class Dumper(Node[BasePayload, None]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._received = 0

    def start(self):
        super().start()

    def stop(self):
        super().stop()
        self.logger.info(f"{self._received} messages received in total")

    def update(self, message: Message[BasePayload]):
        self._received += 1
        self.dump_json(message, f"message_{message.version}.json")
        self.logger.info(
            f"message {message.version} received from: {message.creator}"
            f" with payload: {message.payload}"
        )
