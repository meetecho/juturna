import typing
import logging

from juturna.components import BaseNode
from juturna.components import Message

from juturna.payloads._payloads import ObjectPayload

from transformers import AutoModelForSeq2SeqLM
from transformers import AutoTokenizer
from transformers import pipeline


class TranslatorNllb(BaseNode[ObjectPayload, ObjectPayload]):
    def __init__(self,
                 model_name: str,
                 tokenizer_name: str,
                 src_language: str,
                 dst_language: str,
                 device: str,
                 max_length: int,
                 **kwargs):
        super().__init__(**kwargs)

        self._tokenizer_name = tokenizer_name
        self._model_name = model_name

        self._src_language = src_language
        self._dst_language = dst_language
        self._device = device
        self._max_length = max_length

        logging.getLogger('transformers').setLevel(logging.ERROR)

    def configure(self):
        ...

    def warmup(self):
        self.logger.info(f'tokenizer: {self._tokenizer_name}')

        self._tokenizer = AutoTokenizer.from_pretrained(
            self._tokenizer_name, src_lang=self._src_language)

        self.logger.info(f'translator: {self._model_name}')
        self._model = AutoModelForSeq2SeqLM.from_pretrained(self._model_name)

        self._translator = pipeline(
            'translation',
            device=self._device,
            model=self._model,
            tokenizer=self._tokenizer,
            src_lang=self._src_language,
            tgt_lang=self._dst_language,
            max_length=self._max_length)

    def set_on_config(self, property: str, value: typing.Any):
        ...

    def start(self):
        # after custom start code, invoke base node start
        super().start()

    def stop(self):
        # after custom stop code, invoke base node stop
        super().stop()

    def destroy(self):
        ...

    def update(self, message: Message[ObjectPayload]):
        payload = message.payload
        cnt = payload['suggestion']

        self.logger.info(f'original   : {cnt or "<SILENCE>"}')

        if cnt == '':
            return

        translation = self._translator([cnt])[0]['translation_text']

        self.logger.info(f'translation: {translation}')

        to_send = Message[ObjectPayload](
            creator=self.name,
            version=message.version,
            payload=ObjectPayload())

        to_send.payload['translation'] = translation

        self.transmit(to_send)
