"""
PrompterOllama

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com
@ Created at: 2025-10-09 10:01:02.530811

Connect with a remote ollama server.
"""

import typing

import ollama

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import ObjectPayload
from juturna.payloads import Draft


class PrompterOllama(Node[ObjectPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(self, endpoint: str, model_name: str, **kwargs):
        """
        Parameters
        ----------
        endpoint : str
            Full address of the remote ollama server.
        model_name : str
            Name of the model to chat with.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._endpoint = endpoint
        self._model_name = model_name

        self._client = ollama.Client(host=self._endpoint)

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
        ollama_query = message.payload['ollama_input']

        to_send = Message[ObjectPayload](
            creator=self.name,
            version=message.version,
            payload=Draft(ObjectPayload),
            timers_from=message,
        )

        with to_send.timeit(self.name):
            response = self._client.chat(
                model=self._model_name, messages=ollama_query
            )

        to_send.payload['ollama_response'] = response.model_dump()

        self.transmit(to_send)
