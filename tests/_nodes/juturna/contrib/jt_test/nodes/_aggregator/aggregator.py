"""
Aggregator

@author: Antonio Bevilacqua
@email: abevilacqua@meetecho.com
@created_at: 2026-01-12 10:50:11

Test node. Collect a number of messages, aggregate their content, then return
the concatenated version.
"""
from juturna.components import Node
from juturna.components import Message

from juturna.payloads._payloads import Batch, AudioPayload


class Aggregator(Node[AudioPayload, Batch]):
    def __init__(self, size: int, **kwargs):
        super().__init__(**kwargs)

        self._size = size
        self._received = 0

    def update(self, message: Message, **kwargs):
        pending = kwargs['state'].setdefault('pending', list())
        pending.append(message)

        if len(pending) < self._size:
            return

        batch = Message[Batch](
            creator=self.name,
            payload=Batch(messages=tuple(pending[: self._size])),
        )
        del pending[: self._size]

        self.dump_json(batch, f'batch_{self._received}.json')

        self._received += 1
