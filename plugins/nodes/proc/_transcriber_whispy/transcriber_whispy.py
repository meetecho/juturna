"""
TranscriberParakeet

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com

Transcribe audio packets using whisper models.
For a full list of available models, see here:
https://github.com/SYSTRAN/faster-whisper
"""

import gc
import collections
import time
import logging

import numpy as np

from faster_whisper import WhisperModel

from juturna.components import Message
from juturna.components import Node

from juturna.payloads import AudioPayload
from juturna.payloads import ObjectPayload
from juturna.payloads import Draft


class TranscriberWhispy(Node[AudioPayload, ObjectPayload]):
    """Node implementation class"""

    def __init__(
        self,
        model_name: str,
        only_local: bool,
        language: str,
        task: str,
        buffer_size: int,
        device: str,
        word_timestamps: bool = True,
        without_timestamps: bool = False,
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
        task : str
            What task to perform.
        buffer_size : int
            Number of messages to accumulate before transcription.
        device : str
            Where to run the model (cpu or cuda device).
        word_timestamps : bool
            Whether to generate timestamps during transcription.
        without_timestamps : bool
            Skip timestamp generation.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._only_local = only_local
        self._model = WhisperModel(
            model_name, local_files_only=self._only_local, device=device
        )
        self._model_name = model_name
        self._buffer_size = buffer_size

        self._language = language
        self._task = task
        self._word_timestamps = word_timestamps
        self._without_timestamps = without_timestamps

        # self._data = collections.deque(maxlen=buffer_size)
        self.logger.info(f'init sources: {self.origins}')

        logging.getLogger('faster_whisper').setLevel(logging.ERROR)
        self.logger.info(f'trx created, model id {id(self._model)}')

    def warmup(self):
        """Warmup the node"""
        self._data = {
            k: collections.deque(maxlen=self._buffer_size) for k in self.origins
        }

        self.logger.info(f'warmup sources: {self.origins}')

    def update(self, message: Message[AudioPayload]):
        """Receive data from upstream, transmit data downstream"""
        self.logger.info(f'received {message.version}')

        origin = message.creator

        to_send = Message[ObjectPayload](
            creator=self.name,
            version=message.version,
            payload=Draft(ObjectPayload),
            timers_from=message,
        )

        to_send.meta['origin'] = origin

        if message.meta['silence']:
            self.logger.info('silence detected, sending silence...')
            to_send.payload['transcript'] = list()
            to_send.timer(self.name, -1)

            self.transmit(to_send)
            self._data[origin].clear()

            self.logger.info(f'sent {to_send.version}')

            return

        self.logger.info('transcribing audio content')
        self._data[origin].append(message)

        speech = [m.payload.audio for m in self._data[origin]]
        speech = np.concatenate(speech)

        transcript, trx_info = self._model.transcribe(
            speech,
            language=self._language,
            task=self._task,
            word_timestamps=self._word_timestamps,
            without_timestamps=self._without_timestamps,
            condition_on_previous_text=False,
            prompt_reset_on_temperature=True,
            vad_filter=False,
        )

        with to_send.timeit(self.name):
            transcript = list(transcript)

        word_list = [
            {
                'word': w.word,
                'start': float(w.start),
                'end': float(w.end),
                'start_abs': float(w.start)
                + self._data[origin][0].payload.start,
                'end_abs': float(w.end) + self._data[origin][0].payload.start,
                'probability': float(w.probability),
            }
            for segment in transcript
            for w in segment.words
        ]

        rescaled = TranscriberWhispy._rescale_trx_words(
            word_list, self._data[origin]
        )

        to_send.payload['transcript'] = rescaled

        self.transmit(to_send)
        self.logger.info(f'transmit: {to_send.version}')

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

    def destroy(self):
        """Destroy the node"""
        self._release_model()

    def _release_model(self):
        self.logger.info(f'releasing model: {self._model_name}')

        if hasattr(self._model, 'model'):
            self.logger.info('purging model object...')
            # self._model.model.unload_model(to_cpu=True)
            del self._model.model
            time.sleep(1)
            gc.collect()

        if hasattr(self._model, 'feature_extractor'):
            self.logger.info('purging feature extractor...')
            del self._model.feature_extractor
            time.sleep(1)
            gc.collect()

        if hasattr(self._model, 'hf_tokenizer'):
            self.logger.info('purging tokenizer...')
            del self._model.hf_tokenizer
            time.sleep(1)
            gc.collect()

        del self._model
        gc.collect()
