"""
Crasher

@author: Antonio Bevilacqua
@email: abevilacqua@meetecho.com
@created_at: 2026-01-08 17:18:49

Test sink node. Accumulate received messages.
"""
from juturna.components import Node
from juturna.components import Message

from juturna.payloads import BasePayload


class Crasher(Node[BasePayload, None]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.messages = list()

    def start(self):
        super().start()

    def stop(self):
        super().stop()

    def update(self, message: Message[BasePayload], **kwargs):
        self.messages.append(message)
