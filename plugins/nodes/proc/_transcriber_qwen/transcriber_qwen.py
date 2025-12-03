"""
TranscriberQwen

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com
@ Created at: 2025-10-07 15:02:51.081160

Transcribe audio waveforms with qwen models.
"""

import collections
import tempfile
import typing

import soundfile as sf
import numpy as np

from nemo.collections.speechlm2 import SALM

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import AudioPayload
from juturna.payloads import ObjectPayload
from juturna.payloads import Draft


class TranscriberQwen(Node[AudioPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(
        self, model_name: str, device: str, buffer_size: int, **kwargs
    ):
        """
        Parameters
        ----------
        model_name : str
            The name of the model to use.
        device : str
            The device to use
        buffer_size : int
            How many messages to accumulate for transcription.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._model_name = model_name
        self._device = device
        self._buffer_size = buffer_size

        self._model = (
            SALM.from_pretrained(self._model_name)
            .bfloat16()
            .eval()
            .to(self._device)
        )

        self._messages = collections.deque(maxlen=self._buffer_size)

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

    def update(self, message: Message[AudioPayload]):
        """Receive data from upstream, transmit data downstream"""
        self.logger.info(f'trx received {message.version}')

        to_send = Message[ObjectPayload](
            creator=self.name,
            version=message.version,
            payload=Draft(ObjectPayload),
            timers_from=message,
        )

        if message.meta['silence']:
            self.logger.info('silence detected, sending silence...')
            to_send.payload['transcript'] = list()
            to_send.timer(self.name, -1)

            self.transmit(to_send)
            self._messages.clear()

            self.logger.info(f'sent {to_send.version}')

            return

        self._messages.append(message)

        speech = [m.payload.audio for m in self._messages]
        speech = np.concatenate(speech)

        prompt = {
            'role': 'user',
            'content': f'Transcribe this: {self._model.audio_locator_tag}',
        }

        with (
            to_send.timeit(self.name),
            tempfile.NamedTemporaryFile(
                suffix='.wav', delete=False
            ) as temp_audio,
        ):
            sf.write(temp_audio.name, speech, samplerate=16000)

            prompt['audio'] = temp_audio.name

            answer_ids = self._model.generate(
                prompts=[[prompt]],
                max_new_tokens=128,
            )

            trx = self._model.tokenizer.ids_to_text(answer_ids[0].cpu())
            to_send.payload['transcript'] = trx

        self.logger.info(f'qwen transcription time: {to_send.timers}')
        self.logger.info(f'trx: {trx}')

        self.transmit(to_send)
