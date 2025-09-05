import gc
import collections
import time
import logging

import numpy as np

from faster_whisper import WhisperModel

from juturna.components import Message
from juturna.components import BaseNode

from juturna.payloads._payloads import AudioPayload
from juturna.payloads._payloads import ObjectPayload


class TranscriberWhispy(BaseNode[AudioPayload, ObjectPayload]):
    def __init__(self,
                 model_name: str,
                 only_local: bool,
                 language: str,
                 task: str,
                 buffer_size: int,
                 word_timestamps: bool = True,
                 without_timestamps: bool = False):
        super().__init__('proc')

        self._only_local = only_local
        self._model = WhisperModel(model_name,
                                   local_files_only=self._only_local)
        self._model_name = model_name

        self._language = language
        self._task = task
        self._word_timestamps = word_timestamps
        self._without_timestamps = without_timestamps

        self._data = collections.deque(maxlen=buffer_size)

        logging.getLogger('faster_whisper').disabled = True
        logging.info(f'trx created, model id {id(self._model)}')

    def update(self, message: Message[AudioPayload]):
        logging.info(f'{self.name} receive: {message.version}')

        to_send = Message[ObjectPayload](
            creator=self.name,
            version=message.version,
            payload=ObjectPayload())

        if message.meta['silence']:
            logging.info('    silence detected, sending silence...')
            to_send.payload['transcript'] = dict()
            to_send.timer(self.name, -1)

            self.transmit(to_send)
            logging.info(f'{self.name} transmit: {to_send.version}')
            self._data.clear()
            logging.info('    silence message sent')

            return

        self._data.append(message)

        logging.info('    non-silence, concatenating...')
        speech = [m.payload.audio for m in self._data]
        speech = np.concatenate(speech)
        logging.info('    non-silence, transcribing...')

        transcript, trx_info = self._model.transcribe(
            speech,
            language=self._language,
            task=self._task,
            word_timestamps=self._word_timestamps,
            without_timestamps=self._without_timestamps,
            condition_on_previous_text=False,
            prompt_reset_on_temperature=True,
            vad_filter=False)

        with to_send.timeit(self.name):
            transcript = list(transcript)

        word_start_abs = (self._data[0].meta['size'] * 
                          self._data[0].meta['sequence_number'])

        word_list = [{
            'word': w.word,
            'start': float(w.start),
            'end': float(w.end),
            'start_abs': float(w.start) + word_start_abs,
            'end_abs': float(w.end) + word_start_abs,
            'probability': float(w.probability)
        } for segment in transcript for w in segment.words]

        rescaled = TranscriberWhispy.rescale_trx_words(word_list, self._data)

        to_send.payload['transcript'] = rescaled

        self.transmit(to_send)
        logging.info(f'{self.name} transmit: {to_send.version}')

    @staticmethod
    def rescale_trx_words(words, buffer):
        if not buffer or not words:
            return list()

        chunk_time_map = list()
        accumulated_time = 0

        for m in buffer:
            
            start_abs = (m.meta['size'] * m.meta['sequence_number'])
            speech_offset_map = []

            for segment in m.meta['speech_timestamps']:
                speech_start_abs = start_abs + segment['start_s']
                speech_end_abs = start_abs + segment['end_s']
                speech_offset_map.append(
                    (speech_start_abs, speech_end_abs, accumulated_time))
                accumulated_time += (segment['end_s'] - segment['start_s'])

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

                    if word_start_rescaled is not None and \
                            word_end_rescaled is not None:
                        break

                if word_start_rescaled is not None and \
                        word_end_rescaled is not None:
                    break

            if word_start_rescaled is not None and \
                    word_end_rescaled is not None:
                rescaled_words.append({
                    'word': word['word'],
                    'start': word_start_rescaled,
                    'end': word_end_rescaled,
                    'probability': word['probability']
                })

        return rescaled_words

    def destroy(self):
        self._release_model()

    def _release_model(self):
        logging.info(f'releasing model: {self._model_name}')

        if hasattr(self._model, 'model'):
            logging.info('purging model object...')
            # self._model.model.unload_model(to_cpu=True)
            del self._model.model
            time.sleep(1)
            gc.collect()

        if hasattr(self._model, 'feature_extractor'):
            logging.info('purging feature extractor...')
            del self._model.feature_extractor
            time.sleep(1)
            gc.collect()

        if hasattr(self._model, 'hf_tokenizer'):
            logging.info('purging tokenizer...')
            del self._model.hf_tokenizer
            time.sleep(1)
            gc.collect()

        del self._model
        gc.collect()
