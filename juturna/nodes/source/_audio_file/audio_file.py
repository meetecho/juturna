"""
AudioFile

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com

Read an audio file and chunk it into smaller audio messages.
"""

import io
import itertools

import av

import av.audio
import av.audio.resampler
import numpy as np

from juturna.names import ComponentStatus
from juturna.components import Node
from juturna.components import Message
from juturna.payloads import AudioPayload


class AudioFile(Node[AudioPayload, AudioPayload]):
    """
    Read in an audio file, chunk it based on the configured length, then make
    them available to the pipe in a real-time fashion.
    """

    def __init__(
        self, file_source: str, block_size: int, audio_rate: int, **kwargs
    ):
        """
        Parameter
        ---------
        file_source : str
            The path of the file to source into the pipeline.
        block_size : int
            Time length of each produced audio chunk.
        audio_rate : int
            Sampling rate of the audio file.
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._file_source = file_source
        self._block_size = block_size
        self._rate = audio_rate

        self._audio = None
        self._audio_chunks = list()
        self._transmitted = 0

    def warmup(self):  # noqa: D102
        resampler = av.audio.resampler.AudioResampler(
            format='s16', layout='mono', rate=self._rate
        )

        raw_buffer = io.BytesIO()
        dtype = None

        with av.open(
            self._file_source, mode='r', metadata_errors='ignore'
        ) as container:
            frames = container.decode(audio=0)
            frames = AudioFile._ignore_invalid_frames(frames)
            frames = AudioFile._group_frames(frames, 500000)
            frames = AudioFile._resample_frames(frames, resampler)

            for frame in frames:
                array = frame.to_ndarray()
                dtype = array.dtype
                raw_buffer.write(array)

        audio = np.frombuffer(raw_buffer.getbuffer(), dtype=dtype)
        audio = audio.astype(np.float32) / 32768.0

        self._audio = audio
        self._audio_chunks = self._get_audio_chunks()

        self.set_source(self._generate_chunks, by=self._block_size, mode='pre')

        self.logger.info('audio loaded')
        self.logger.info(f'duration: {len(audio) / self._rate}')

    def _generate_chunks(self) -> Message[AudioPayload] | None:
        try:
            return Message[AudioPayload](
                creator=self.name,
                payload=AudioPayload(
                    audio=self._audio_chunks[self._transmitted],
                    sampling_rate=self._rate,
                    channels=1,
                    start=self._block_size * self._transmitted,
                    end=self._block_size * self._transmitted + self._block_size,
                ),
            )
        except IndexError:
            self.logger.info('sending None')

            return None

    def _get_audio_chunks(self) -> list:
        chunks = list()
        wave_len = self._block_size * self._rate

        for chunk in AudioFile._chunker(self._audio, wave_len):
            if len(chunk) < wave_len:
                chunk = np.pad(
                    chunk,
                    (0, wave_len - len(chunk)),
                    mode='constant',
                    constant_values=0,
                )

            chunks.append(chunk)

        return chunks

    def update(self, message: Message[AudioPayload]):  # noqa: D102
        if message is None:
            self.logger.info('audio file done, stopping...')

            self.stop()
            self.status = ComponentStatus.STOPPED

            return

        message.version = self._transmitted
        message.meta['session_id'] = self.pipe_id
        message.meta['size'] = self._block_size

        self.transmit(message)
        self._transmitted += 1

    @staticmethod
    def _ignore_invalid_frames(frames):
        iterator = iter(frames)

        while True:
            try:
                yield next(iterator)
            except StopIteration:
                break
            except av.error.InvalidDataError:
                continue

    @staticmethod
    def _chunker(seq, size):
        return (seq[pos : pos + size] for pos in range(0, len(seq), size))

    @staticmethod
    def _group_frames(frames, num_samples=None):
        fifo = av.audio.fifo.AudioFifo()

        for frame in frames:
            frame.pts = None
            fifo.write(frame)

            if num_samples is not None and fifo.samples >= num_samples:
                yield fifo.read()

        if fifo.samples > 0:
            yield fifo.read()

    @staticmethod
    def _resample_frames(frames, resampler):
        for frame in itertools.chain(frames, [None]):
            yield from resampler.resample(frame)
