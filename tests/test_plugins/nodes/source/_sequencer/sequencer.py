"""
Sequencer

@author: Antonio Bevilacqua
@email: abevilacqua@meetecho.com
@created_at: 2026-01-08 17:17:56

Test node. Sourcing numeric sequences of configurable length at a configurable
rate.
"""
import time
import typing

import numpy as np

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import AudioPayload


class Sequencer(Node[None, AudioPayload]):
    def __init__(
        self,
        sample_length_sec: int,
        sample_rate: int,
        sample_tone: int,
        audio_format: str,
        channels: int,
        rate: float, **kwargs
    ):
        super().__init__(**kwargs)

        self._sample_length_sec = sample_length_sec
        self._sample_rate = sample_rate
        self._sample_tone = sample_tone
        self._audio_format = audio_format
        self._channels = channels

        self._rate = rate
        self._transmitted = 0
        self._transmitting = True

        self.set_source(self._generate, by=1/self._rate, mode='pre')

    def _generate(self):
        return Message[AudioPayload](
            creator=self.name,
            version=self._transmitted,
            payload=AudioPayload(
                audio=Sequencer.generate_tone(
                    self._sample_length_sec,
                    self._sample_rate,
                    self._channels,
                    self._sample_tone,
                    self._audio_format
                    ),
                sampling_rate=self._sample_rate,
                audio_format=self._audio_format,
                channels=self._channels,)
            )

    def start(self):
        super().start()

    def stop(self):
        super().stop()

    def update(self, message: Message[AudioPayload]):
        self.transmit(message)
        self.dump_json(message, f'message_{self._transmitted}.json')

        self._transmitted += 1

    @staticmethod
    def generate_tone(
        duration: float = 1.0,
        sample_rate: int = 16_000,
        channels: int = 1,
        freq: int = 440,
        format: str = 'int16'
    ):
        num_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)
        signal = np.sin(2 * np.pi * freq * t)

        if channels == 1:
            audio = signal.reshape(-1, 1)
        elif channels == 2:
            audio = np.column_stack((signal, signal))
        else:
            audio = np.tile(signal.reshape(-1, 1), (1, channels))

        if format == 'int16':
            max_val = 32767
            audio = (audio * max_val).astype(np.int16)
        elif format == 'float32':
            audio = audio.astype(np.float32)

        return audio
