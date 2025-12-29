"""
TranslatorNllb

@Author: Antonio Bevilacqua
@Email: abevilacqua@meetecho.com

Use NLLB to translate text. Find the supported language codes here:
https://github.com/facebookresearch/flores/blob/main/flores200/README.md#languages-in-flores-200

This node offers basic, quick translation support. It is possible to specify
whether received messages should be buffered before translation using the
`buffer_length` configuration item. Setting this to 1 has the effect of
translating each individual message received.

"""

import typing
import collections
import logging

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import ObjectPayload
from juturna.payloads import Draft

from transformers import AutoModelForSeq2SeqLM
from transformers import AutoTokenizer
from transformers import pipeline


class TranslatorNllb(Node[ObjectPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(
        self,
        model_name: str,
        tokenizer_name: str,
        src_language: str,
        dst_language: str,
        device: str,
        target_prop: list,
        max_length: int,
        buffer_length: int,
        **kwargs,
    ):
        """
        Parameters
        ----------
        model_name : str
            Translation model to use for the translation.
        tokenizer_name : str
            Tokenizer model to use for the translation.
        src_language : str
            Language of the incoming text.
        dst_language : str
            Destination language to translate the text into.
        device : str
            Where to use the model, cpu or cuda.
        target_prop : list
            Accessors to the message payload to get the target text.
        max_length : int
            Text max length.
        buffer_length : int
            How many messages to accumulate before translation.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._tokenizer_name = tokenizer_name
        self._model_name = model_name

        self._src_language = src_language
        self._dst_language = dst_language
        self._device = device
        self._target_prop = target_prop
        self._max_length = max_length
        self._buffer_length = buffer_length

        self._buffer = collections.deque(maxlen=buffer_length)

        logging.getLogger('transformers').setLevel(logging.ERROR)

    def configure(self):
        """Configure the node"""
        ...

    def warmup(self):
        """Warmup the node"""
        self.logger.info(f'tokenizer: {self._tokenizer_name}')

        self._tokenizer = AutoTokenizer.from_pretrained(
            self._tokenizer_name, src_lang=self._src_language
        )

        self.logger.info(f'translator: {self._model_name}')
        self._model = AutoModelForSeq2SeqLM.from_pretrained(self._model_name)

        self._translator = pipeline(
            'translation',
            device=self._device,
            model=self._model,
            tokenizer=self._tokenizer,
            src_lang=self._src_language,
            tgt_lang=self._dst_language,
            max_length=self._max_length,
        )

    def set_on_config(self, prop: str, value: typing.Any):
        """Hot-swap node propertoes"""
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

    def update(self, message: Message[ObjectPayload]):
        """Receive data from upstream, transmit data downstream"""
        self._buffer.append(message)

        if len(self._buffer) < self._buffer_length:
            return

        content = ' '.join([m.payload['suggestion'] for m in self._buffer])
        ids = [m.version for m in self._buffer]

        self.logger.info(f'original   : {content or "<SILENCE>"}')
        self._buffer.clear()

        if content.isspace():
            return

        translation = self._translator([content])[0]['translation_text']

        self.logger.info(f'translation: {translation}')

        to_send = Message[ObjectPayload](
            creator=self.name,
            version=message.version,
            payload=Draft(ObjectPayload),
            timers_from=message,
        )

        to_send.payload['translation'] = translation
        to_send.payload['ids'] = ids

        self.transmit(to_send)
