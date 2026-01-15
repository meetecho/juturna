"""
Aggregator

@author: Antonio Bevilacqua
@email: abevilacqua@meetecho.com
@created_at: 2026-01-12 10:50:11

Test node. Collect a number of messages, aggregate their content, then return
the concatenated version.
"""
import typing

from juturna.components import Node
from juturna.components import Message

from juturna.payloads._payloads import Batch, AudioPayload


class Aggregator(Node[Batch, AudioPayload]):
    def __init__(self, size: int, **kwargs):
        super().__init__(**kwargs)

        self._size = size
        self._received = 0

    def update(self, message: Message):
        self.dump_json(message, f'batch_{self._received}.json')

        self._received += 1

    def next_batch(
        self,
        sources: dict[str, list[Message]]
    ) -> dict[str, list[int]]:
        marked = dict()
        total_available = sum(len(msgs) for msgs in sources.values())

        if self._size > total_available:
            return dict()

        remaining = self._size

        for source, messages in sources.items():
            if remaining == 0:
                break

            count_to_take = min(remaining, len(messages))

            if count_to_take > 0:
                marked[source] = list(range(count_to_take))
                remaining -= count_to_take

        return marked
