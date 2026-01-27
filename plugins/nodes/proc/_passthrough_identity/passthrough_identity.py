"""
PassthroughIdentity

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com

Test node: return input messages after a delay.
"""

import time

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import BasePayload


class PassthroughIdentity(Node[BasePayload, BasePayload]):
    """Node implementation class"""

    def __init__(self, delay: int, **kwargs):
        """
        Parameters
        ----------
        delay : int
            Wait time before returning input messages to the output.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._delay = delay
        self._transmitted = 0

    def update(self, message: Message[BasePayload]):
        """Receive a message from downstream, transmit a message upstream"""
        self.logger.info(
            f'message {message.version} received from: {message.creator}'
        )

        to_send = Message[BasePayload](
            creator=self.name,
            version=message.version,
            payload=message.payload.clone(),
            timers_from=message,
        )

        to_send.meta = dict(message.meta)

        self._transmitted += 1

        with to_send.timeit(f'{self.name}_delay'):
            time.sleep(self._delay)

        self.transmit(to_send)

    def next_batch(self, sources: dict) -> dict:
        """Synchronisation policy"""
        self.logger.info('using custom policy')
        self.logger.info(f'expected sources: {self.origins}')

        return {source: list(range(len(sources[source]))) for source in sources}
