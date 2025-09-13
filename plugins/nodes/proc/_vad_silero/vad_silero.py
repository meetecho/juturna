import copy

from collections import deque

import silero_vad
import torch
import numpy as np

from juturna.components import Message
from juturna.components import BaseNode

from juturna.payloads._payloads import AudioPayload


class VadSilero(BaseNode[AudioPayload, AudioPayload]):
    def __init__(self,
                 rate: int,
                 threshold: float,
                 min_speech_duration_ms: int,
                 max_speech_duration_s: float | str,
                 min_silence_duration_ms: int,
                 speech_pad_ms: int,
                 keep: int,
                 **kwargs):
        super().__init__(**kwargs)

        self._model = silero_vad.load_silero_vad()
        self._rate = rate
        self._threshold = threshold
        self._min_speech_duration_ms = min_speech_duration_ms
        self._max_speech_duration_s = float(max_speech_duration_s)
        self._min_silence_duration_ms = min_silence_duration_ms
        self._speech_pad_ms = speech_pad_ms
        self._keep = keep

        self._data = deque(maxlen=self._keep)

    def update(self, message: Message[AudioPayload]):
        assert isinstance(self._data, deque)
        self.logger.info(f'{self.name} receive: {message.version}')

        self._data.append(message)

        waveform = [m.payload.audio for m in self._data]
        waveform = np.concatenate(waveform)
        version = self._data[-1].version
        block_size = self._data[-1].meta['size']

        to_send = Message[AudioPayload](
            creator=self.name,
            version=message.version,
            payload=AudioPayload.clone(message.payload))

        to_send.meta = copy.deepcopy(message.meta)
        to_send.timers = copy.deepcopy(message.timers)

        to_send.meta['silence'] = False
        to_send.meta['size'] = block_size
        to_send.meta['sequence_number'] = version
        to_send.meta['original_audio'] = waveform

        with to_send.timeit(self.name):
            speech_timestamps, clip, duration_after_vad = \
                self.run_vad(waveform)

        to_send.payload.audio = clip
        to_send.meta['duration_after_vad'] = duration_after_vad

        if duration_after_vad == 0.0:
            to_send.meta['silence'] = True

            self.transmit(to_send)
            self.logger.info(f'{self.name} transmit: {to_send.version}')

            return

        to_send.meta['speech_timestamps'] = speech_timestamps

        self.transmit(to_send)
        self.logger.info(f'{self.name} transmit: {to_send.version}')

    def destroy(self):
        self._data = None

    def run_vad(self, audio: np.ndarray) -> tuple:
        speech_ts = silero_vad.get_speech_timestamps(
            audio,
            self._model,
            threshold=self._threshold,
            sampling_rate=self._rate,
            min_speech_duration_ms=self._min_speech_duration_ms,
            max_speech_duration_s=self._max_speech_duration_s,
            min_silence_duration_ms=self._min_silence_duration_ms,
            speech_pad_ms=self._speech_pad_ms)

        if len(speech_ts) > 0:
            clipped_audio = silero_vad.collect_chunks(
                tss=speech_ts,
                wav=torch.from_numpy(audio))
        else:
            clipped_audio = np.ndarray(0, dtype=np.float32)

        duration_after_vad = clipped_audio.shape[0] / self._rate

        for idx, _ in enumerate(speech_ts):
            speech_ts[idx]['start_s'] = speech_ts[idx]['start'] / self._rate
            speech_ts[idx]['end_s'] = speech_ts[idx]['end'] / self._rate

        return speech_ts, clipped_audio, duration_after_vad