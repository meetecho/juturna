import logging

from collections import deque

import torch
import silero_vad
import numpy as np

from juturna.components import Message
from juturna.components import BaseNode


class VadSilero(BaseNode):
    def __init__(self, rate: int, threshold: float, keep: int):
        super().__init__('proc')

        self._model = silero_vad.load_silero_vad()
        self._rate = rate
        self._threshold = threshold
        self._keep = keep
        self._data = deque(maxlen=self._keep)

    def run_vad(self, audio: np.ndarray) -> tuple:
        speech_ts = silero_vad.get_speech_timestamps(
            torch.from_numpy(audio),
            self._model,
            threshold=self._threshold,
            sampling_rate=self._rate)
        clipped_audio = silero_vad.collect_chunks(
            speech_ts,
            torch.from_numpy(audio)) if len(speech_ts) > 0 else audio
        duration_after_vad = clipped_audio.shape[0] / self._rate

        for idx, ts in enumerate(speech_ts):
            speech_ts[idx]['start_s'] = speech_ts[idx]['start'] / self._rate
            speech_ts[idx]['end_s'] = speech_ts[idx]['end'] / self._rate

        return speech_ts, clipped_audio, duration_after_vad

    def update(self, message: Message):
        logging.info(f'{self.name} receive: {message.version}')
        self._data.append(message)

        waveform = [m.payload for m in self._data]
        waveform = np.concatenate(waveform)
        version = self._data[-1].version
        block_size = self._data[-1].meta['size']

        to_send = Message.from_message(message, keep_meta=True)
        to_send.created_by = self.name
        to_send.version = message.version

        to_send.payload = { 'waveform': waveform }

        to_send.meta['silence'] = False
        to_send.meta['size'] = block_size
        to_send.meta['rate'] = self._rate
        to_send.meta['sequence_number'] = version
        to_send.meta['start_abs'] = block_size * version
        to_send.meta['end_abs'] = to_send.meta['start_abs'] + block_size

        with to_send.timeit(self.name):
            speech_timestamps, clip, duration_after_vad = \
                self.run_vad(waveform)

        to_send.meta['duration_after_vad'] = duration_after_vad

        if duration_after_vad == 0.0:
            to_send.meta['silence'] = True

            self.transmit(to_send)
            logging.info(f'{self.name} transmit: {to_send.version}')

            return

        to_send.payload['speech_waveform'] = clip
        to_send.meta['speech_timestamps'] = speech_timestamps

        self.transmit(to_send)
        logging.info(f'{self.name} transmit: {to_send.version}')

    def destroy(self):
        self._data = None
