"""
PrompterOllama

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com
@ Created at: 2025-10-09 10:01:02.530811

Connect with a remote ollama server.
"""

import typing
import json

import ollama

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import ObjectPayload
from juturna.payloads import Batch
from juturna.payloads import Draft


class PrompterOllama(Node[ObjectPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(
        self,
        endpoint: str,
        model_name: str,
        keep_alive: int,
        setup_file: str,
        think: bool,
        every: int,
        **kwargs,
    ):
        """
        Parameters
        ----------
        endpoint : str
            Full address of the remote ollama server.
        model_name : str
            Name of the model to chat with.
        keep_alive : int
            How ollama should manage loaded models (-1 to keep them in memory
            indefinitely, 0 to unload them after every use).
        setup_file : str
            Path of the model setup file. This file contains setup items for the
            model being used: output format, and system message.
        think : bool
            Enable / disable model thinking.
        every : int
            How many messages to buffer before querying the model.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._endpoint = endpoint
        self._model_name = model_name
        self._keep_alive = keep_alive
        self._think = think
        self._every = every

        with open(setup_file) as f:
            self._setup = json.load(f)

        self._format = None
        self._system_msg = None

        self._client = ollama.Client(host=self._endpoint)

    def configure(self):
        """Configure the node"""
        ...

    def warmup(self):
        """Warmup the node"""
        self._format = self._setup.get('format', None)
        self._system_msg = list(
            filter(
                lambda msg: msg['role'] == 'system',
                self._setup.get('messages', list()),
            )
        )

        _ = self._client.generate(
            model=self._model_name, prompt='', keep_alive=self._keep_alive
        )

        self.logger.info(f'model {self._model_name} loaded')
        self.logger.info(f'system prompt: {self._system_msg}')

    def set_on_config(self, prop: str, value: typing.Any):
        """Hot-swap node properties"""
        ...

    def start(self):
        """Start the node"""
        super().start()

    def stop(self):
        """Stop the node"""
        super().stop()

    def destroy(self):
        """Destroy the node"""
        ...

    def update(self, message: Message[ObjectPayload | Batch]):
        """Receive data from upstream, transmit data downstream"""
        if isinstance(message.payload, Batch):
            content = ' '.join(
                m.payload['prompt'] for m in message.payload.messages
            )
            source = [m.payload for m in message.payload.messages]
        else:
            content = message.payload['prompt']
            source = message.payload

        user_query = [
            {
                'role': 'user',
                'content': content,
            }
        ]

        to_send = Message[ObjectPayload](
            creator=self.name,
            version=message.version,
            payload=Draft(ObjectPayload),
            timers_from=message,
        )

        with to_send.timeit(self.name):
            response = self._client.chat(
                model=self._model_name,
                format=self._format,
                messages=self._system_msg + user_query,
                think=self._think,
            )

        if isinstance(self._format, dict):
            try:
                response_dict = json.loads(response['message']['content'])
            except Exception:
                response_dict = dict()

        to_send.payload['ollama_response'] = response.model_dump()
        to_send.payload['source'] = source
        to_send.payload['structured_response'] = response_dict

        self.transmit(to_send)

    def next_batch(  # noqa: D102
        self, sources: dict[str, list[Message]]
    ) -> dict[str, list[int]]:
        """Mark messages to be transmitted in batch"""
        marked = dict()
        total_available = sum(len(msgs) for msgs in sources.values())

        if self._every > total_available:
            return dict()

        remaining = self._every

        for source, messages in sources.items():
            if remaining == 0:
                break

            count_to_take = min(remaining, len(messages))

            if count_to_take > 0:
                marked[source] = list(range(count_to_take))
                remaining -= count_to_take

        return marked
