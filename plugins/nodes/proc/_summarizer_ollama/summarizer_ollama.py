"""
SummarizerOllama

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com

Generate summaries from a stream of data chunks. The node expects input data in
the form of objects containing a content id and a textual chunk. The content id
will be used to manage the summary history, so that whenever the content id
changes, the history will be flushed.
"""

import json
import collections
import time

import ollama

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import ObjectPayload
from juturna.payloads import Batch
from juturna.payloads import Draft

from juturna.utils.proc_utils import safe_exec


class SummarizerOllama(Node[ObjectPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(
        self,
        endpoint: str,
        model_name: str,
        keep_alive: int,
        setup_file: str,
        every: int,
        max_topics: int,
        max_history: int,
        temperature: float,
        include: list,
        exclude: list,
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
        every : int
            How many messages to buffer before querying the model.
        max_topics : int
            Maximum number of topics the node can follow during summarization.
            If 0, no maximum number of topics is set.
        max_history : int
            Maximum number of history messages to save for the topics. If -1,
            the history message is unlimited.
        temperature : float
            Temperature option to pass to the model.
        include : list
            List of topics to accept. If provided, trumps max_topics and does
            not apply topic_policy. All topics not included in this list will be
            ignored.
        exclude : list
            List of topics to always reject.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._endpoint = endpoint
        self._model_name = model_name
        self._keep_alive = keep_alive
        self._every = every

        self._max_topics = max_topics
        self._max_history = max_history
        self._temperature = temperature

        self._include = include or None
        self._exclude = exclude or None

        self._topic_history = dict()

        if self._include:
            self._topic_history = {
                topic: {
                    'last_updated': -1,
                    'messages': collections.deque()
                    if not self._max_history
                    else collections.deque(maxlen=self._max_history),
                }
                for topic in self._include
            }

        with open(setup_file) as f:
            self._setup = json.load(f)

        self._format = None
        self._system_msg = None
        self._step = 0

        self._client = ollama.Client(host=self._endpoint)

    def warmup(self):
        """Warmup the node"""
        self._format = self._setup.get('format', None)
        self._system_msg = list(
            filter(
                lambda msg: msg['role'] == 'system',
                self._setup.get('messages', list()),
            )
        )[0]

        _ = self._client.generate(
            model=self._model_name,
            prompt='',
        )

        self.logger.info(f'model {self._model_name} loaded')

    @safe_exec
    def update(self, message: Message[ObjectPayload | Batch]):
        """Receive data from upstream, transmit data downstream"""
        msgs = (
            message.payload.messages
            if isinstance(message.payload, Batch)
            else [message]
        )

        topic = msgs[0].payload['topic']

        self.logger.info(f'received message for topic <{topic}>')

        if self._exclude and topic in self._exclude:
            self.logger.info(f'topic not allowed: {topic}')

            return

        query_messages = [
            {'role': 'user', 'content': m.payload['chunk']} for m in msgs
        ]
        source = [m.payload for m in msgs]
        topic_history = self._topic_history.get(topic, dict())
        history_messages = list(topic_history.get('messages', list()))

        self.logger.info(f'topic history: {len(history_messages)}')

        query_messages = [self._system_msg] + history_messages + query_messages

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
                messages=query_messages,
                options={'temperature': self._temperature},
                think=False,
            )

        if isinstance(self._format, dict):
            try:
                response_dict = json.loads(response['message']['content'])
            except Exception:
                response_dict = dict()

            # TODO: this depends on the format provided in the setup file!
            summary = (
                response_dict.get('summary')
                if isinstance(response_dict, dict)
                else response_dict
            )
        else:
            response_dict = None
            summary = response.message.content

        to_send.payload['ollama_response'] = response.model_dump()
        to_send.payload['structured_response'] = response_dict
        to_send.payload['source'] = source
        to_send.payload['topic'] = topic
        to_send.payload['history'] = self._normalize_history(topic_history)

        self.logger.info('transmitting')
        self.transmit(to_send)

        if not summary:
            return

        self._update_history(topic, summary)

    def _update_history(self, topic: str, summary: str):
        if isinstance(summary, dict):
            summary = json.dumps(summary)

        msg = {'role': 'user', 'content': summary}

        if topic in self._topic_history:
            self.logger.info(f'topic <{topic}> in history, updating')
            self._topic_history[topic]['messages'].append(msg)
            self._topic_history[topic]['last_updated'] = time.time()

            return

        if self._max_topics and len(self._topic_history) == self._max_topics:
            oldest_topic = min(
                self._topic_history,
                key=lambda t: self._topic_history[t]['last_updated'],
            )

            self.logger.info(f'history full, dropping topic <{oldest_topic}>')

            del self._topic_history[oldest_topic]

        self.logger.info(f'adding new topic <{topic}> in history')

        self._topic_history[topic] = {
            'messages': collections.deque([msg])
            if not self._max_history
            else collections.deque([msg], maxlen=self._max_history),
            'last_updated': time.time(),
        }

    def _normalize_history(self, history: dict) -> dict:
        return {
            'messages': list(history.get('messages', list())),
            'last_updated': history.get('last_updated', -1),
        }

    def next_batch(
        self, sources: dict[str, list[Message]]
    ) -> dict[str, list[int]]:
        """Mark messages to be transmitted in batch"""
        best_source = None
        best_topic_indices = list()
        max_source_length = -1
        max_topic_count = -1

        for source_name, messages in sources.items():
            source_length = len(messages)

            topic_to_indices: dict[str, list[int]] = dict()

            for idx, msg in enumerate(messages):
                topic = msg.payload['topic']

                topic_to_indices.setdefault(topic, list()).append(idx)

            for _, indices in topic_to_indices.items():
                topic_count = len(indices)

                if (
                    topic_count >= self._every
                    and (source_length > max_source_length)
                    or (
                        source_length == max_source_length
                        and topic_count > max_topic_count
                    )
                ):
                    best_source = source_name
                    best_topic_indices = indices
                    max_source_length = source_length
                    max_topic_count = topic_count

        if best_source is not None:
            return {best_source: best_topic_indices[: self._every]}

        return dict()
