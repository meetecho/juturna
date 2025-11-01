import time

from juturna.components import Node
from juturna.components import Message

from juturna.payloads._payloads import BasePayload


class PassthroughIdentity(Node[BasePayload, BasePayload]):
    def __init__(self, delay: int, **kwargs):
        super().__init__(**kwargs)

        self._delay = delay
        self._transmitted = 0

    def update(self, message: Message[BasePayload]):
        self.logger.info(f'message {message.version} received from: {message.creator}')
        to_send = Message[BasePayload](
            creator=self.name,
            version=message.version,
            payload=message.payload.clone(),
            timers_from=message,
        )

        self._transmitted += 1

        with to_send.timeit(f'{self.name}_delay'):
            time.sleep(self._delay)

        self.transmit(to_send)
