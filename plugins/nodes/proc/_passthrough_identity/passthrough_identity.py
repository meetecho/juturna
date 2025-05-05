import time

from juturna.components import BaseNode
from juturna.components import Message


class PassthroughIdentity(BaseNode):
    def __init__(self, delay: int):
        super().__init__('proc')

        self._delay = delay
        self._transmitted = 0

    def update(self, message: Message):
        to_send = Message.from_message(message, keep_meta=True)
        to_send.version = self._transmitted
        self._transmitted += 1

        with to_send.timeit(f'{self.name}_delay'):
            time.sleep(self._delay)

        self.transmit(to_send)
