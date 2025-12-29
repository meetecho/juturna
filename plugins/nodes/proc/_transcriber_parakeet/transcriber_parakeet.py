"""
TranscriberParakeet

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com
@ Created at: 2025-10-06 11:00:00.889446

Transcribe audio packets using parakeet models.
"""

import collections
import logging

import torch
import omegaconf

import nemo.collections.asr as nemo_asr
import numpy as np

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import AudioPayload
from juturna.payloads import ObjectPayload
from juturna.payloads import Draft


class TranscriberParakeet(Node[AudioPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(
        self,
        model_name: str,
        only_local: bool,
        language: str,
        word_timestamps: bool,
        buffer_size: int,
        **kwargs,
    ):
        """
        Parameters
        ----------
        model_name : str
            Name of the model to use for transcription.
        only_local : bool
            Only use local model and prevent the node from downloading.
        language : str
            Source audio language.
        buffer_size : int
            Number of messages to accumulate before transcription.
        word_timestamps : bool
            Whether to generate timestamps during transcription.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)
        logging.getLogger('nemo_logger').setLevel(logging.ERROR)

        self._only_local = only_local
        self._model_name = model_name
        self._model = (
            nemo_asr.models.ASRModel.from_pretrained(
                model_name=self._model_name
            )
            if not self._only_local
            else nemo_asr.models.ASRModel.restore_from(self._model_name)
        )

        self._model.change_attention_model('rel_pos_local_attn', [256, 256])
        self._model.change_subsampling_conv_chunking_factor(1)
        self._model.to(torch.bfloat16)

        with omegaconf.open_dict(self._model.cfg.decoding):
            self._model.cfg.decoding.preserve_alignments = True

            if not hasattr(self._model.cfg.decoding, 'confidence_cfg'):
                self._model.cfg.decoding.confidence_cfg = (
                    omegaconf.OmegaConf.create(
                        {
                            'preserve_frame_confidence': True,
                            'preserve_word_confidence': True,
                        }
                    )
                )
            else:
                self._model.cfg.decoding.confidence_cfg.preserve_frame_confidence = True  # noqa: E501
                self._model.cfg.decoding.confidence_cfg.preserve_word_confidence = True  # noqa: E501

        self._model.change_decoding_strategy(self._model.cfg.decoding)

        self._language = language
        self._word_timestamps = word_timestamps
        self._buffer_size = buffer_size
        self._messages = collections.deque(maxlen=self._buffer_size)

        self.logger.info('parakeet transcriber created')

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
            self.logger.info('silence detected in transcriber')
            to_send.payload['transcript'] = list()
            to_send.timer(self.name, -1)

            self.transmit(to_send)
            self._messages.clear()

            self.logger.info(f'trx sent {to_send.version}')

            return

        self.logger.info('transcribing audio content...')
        self._messages.append(message)

        speech = [m.payload.audio for m in self._messages]
        speech = np.concatenate(speech)

        with to_send.timeit(self.name):
            transcript = self._model.transcribe(
                speech, timestamps=self._word_timestamps, return_hypotheses=True
            )

        # this is an object of type Hypothesis
        trx_obj = transcript[0]

        word_list = [
            {
                'word': w['word'] + ' ',
                'start': float(w['start']),
                'end': float(w['end']),
                'start_abs': float(w['start'])
                + self._messages[0].payload.start,
                'end_abs': float(w['end']) + self._messages[0].payload.start,
                'probability': float(p),
            }
            for w, p in zip(
                trx_obj.timestamp['word'], trx_obj.word_confidence, strict=True
            )
        ]

        rescaled = TranscriberParakeet._rescale_trx_words(
            word_list, self._messages
        )

        to_send.payload['transcript'] = rescaled

        self.transmit(to_send)
        self.logger.info('transcription done')

    @staticmethod
    def _rescale_trx_words(words, buffer):
        if not buffer or not words:
            return list()

        chunk_time_map = list()
        accumulated_time = 0

        for m in buffer:
            start_abs = m.payload.start
            speech_offset_map = []

            for segment in m.meta['speech_timestamps']:
                speech_start_abs = start_abs + segment['start_s']
                speech_end_abs = start_abs + segment['end_s']
                speech_offset_map.append(
                    (speech_start_abs, speech_end_abs, accumulated_time)
                )
                accumulated_time += segment['end_s'] - segment['start_s']

            chunk_time_map.append((start_abs, speech_offset_map))

        rescaled_words = list()

        for word in words:
            word_start_rescaled = None
            word_end_rescaled = None

            for _, speech_map in chunk_time_map:
                for sp_start_abs, sp_end_abs, offset in speech_map:
                    start = word['start']
                    end = word['end']

                    if offset <= start < offset + (sp_end_abs - sp_start_abs):
                        word_start_rescaled = sp_start_abs + (start - offset)

                    if offset <= end < offset + (sp_end_abs - sp_start_abs):
                        word_end_rescaled = sp_start_abs + (end - offset)

                    if (
                        word_start_rescaled is not None
                        and word_end_rescaled is not None
                    ):
                        break

                if (
                    word_start_rescaled is not None
                    and word_end_rescaled is not None
                ):
                    break

            if (
                word_start_rescaled is not None
                and word_end_rescaled is not None
            ):
                rescaled_words.append(
                    {
                        'word': word['word'],
                        'start': word_start_rescaled,
                        'end': word_end_rescaled,
                        'probability': word['probability'],
                    }
                )

        return rescaled_words
