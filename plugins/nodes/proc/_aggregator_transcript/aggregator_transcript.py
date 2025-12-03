"""
AggregatorTranscript

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com
@ Created at: 2025-10-09 14:15:46.852401

Aggregate transcription results and send them to a LLM.
"""

import collections
import pathlib
import typing

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import ObjectPayload
from juturna.payloads import Draft


class AggregatorTranscript(Node[ObjectPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(self, system_input_template: str, **kwargs):
        """
        Parameters
        ----------
        system_input_template : str
            Name of the system input template file.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._transcription_queue = collections.deque(maxlen=2)
        self._system_input_template_path = system_input_template

        with open(
            pathlib.Path(self.static_path, self._system_input_template_path)
        ) as f:
            self._system_input_template = f.read()

    def configure(self):
        """Configure the node"""
        ...

    def warmup(self):
        """Warmup the node"""
        ...

    def set_on_config(self, prop: str, value: typing.Any):
        """Hot-swap node properties"""
        ...

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
        transcript = message.payload['transcript']

        if transcript == '' or transcript == list():
            self._transcription_queue.clear()
            self.logger.info('no aggregation needed, audio is silent')

            return

        to_send = Message[ObjectPayload](
            creator=self.name,
            version=message.version,
            payload=Draft(ObjectPayload),
            timers_from=message,
        )

        self._transcription_queue.append(transcript)

        with to_send.timeit(self.name):
            system_input = self.compile_template(
                self._system_input_template_path, dict()
            )

        to_send.payload['ollama_input'] = [
            {'role': 'system', 'content': system_input},
            {
                'role': 'user',
                'content': str({'sentences': list(self._transcription_queue)}),
            },
        ]

        self.logger.info('aggregated, sending to ollama')
        self.transmit(to_send)
