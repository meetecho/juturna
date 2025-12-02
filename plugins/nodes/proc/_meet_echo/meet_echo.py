"""
MeetEcho

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com
@ Created at: 2025-10-06 09:56:59.500412

Detect trigger words for command activations.
"""

import string
import typing

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import ObjectPayload
from juturna.payloads import Draft


class MeetEcho(Node[ObjectPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(self, activation: str, target: str, **kwargs):
        """
        Parameters
        ----------
        activation : str
            Activation trigger for command execution.
        target : str
            Target keyword in received messages.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._activation = activation
        self._messages = list()
        self._accumulating = False

        self._sent = 0

    def configure(self):
        """Configure the node"""
        ...

    def warmup(self):
        """Warmup the node"""
        ...

    def set_on_config(self, prop: str, value: typing.Any):
        """Hot-swap node properties"""
        if prop == 'activation':
            self._activation = value

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
        ...

    def update(self, message: Message[ObjectPayload]):
        """Receive data from upstream, transmit data downstream"""
        # not accumulating, no activation: ignore
        if not self._accumulating and not self._has_activation(
            message.payload[self._target]
        ):
            self.logger.info('meet echo inactive - skipping')

            return

        # not accumulating, activation: start accumulating
        if not self._accumulating and self._has_activation(
            message.payload[self._target]
        ):
            self._accumulating = True

            return

        # accumulating, message content: keep accumulating
        if self._accumulating and not message.payload['silence']:
            self._messages.append(message)

            return

        # accumulating, silence: command is complete
        if self._accumulating and message.payload['silence']:
            full_query = ' '.join(
                [m.payload['suggestion'] for m in self._messages]
            )

            self._accumulating = False
            self._messages = list()

            to_send = Message[ObjectPayload](
                creator=self.name,
                version=self._sent,
                payload=Draft(ObjectPayload),
                timers_from=message,
            )

            to_send.payload['input_query'] = full_query

            self.transmit(to_send)
            self._sent += 1

    def _has_activation(self, text: str):
        clean_activation = (
            self._activation.strip()
            .lower()
            .translate(str.maketrans('', '', string.punctuation))
        )

        clean_text = (
            text.strip()
            .lower()
            .translate(str.maketrans('', '', string.punctuation))
        )

        return clean_activation in clean_text
