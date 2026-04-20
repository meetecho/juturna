"""
AudioRtpAv

@author: Antonio Bevilacqua, Paolo Saviano
@email: b3by.in.th3.sky@gmail.com, psaviano@meetecho.com
@created_at: 2025-12-16 21:54:39

Consume RTP audio streams using PyAv.
"""

import threading
import pathlib

import av
import numpy as np

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import AudioPayload
from juturna.components import _resource_broker as rb
from juturna.meta import JUTURNA_THREAD_JOIN_TIMEOUT


class AudioRtpAv(Node[AudioPayload, AudioPayload]):
    """Node implementation class"""

    _SDP_TEMPLATE_NAME: str = 'remote_source.sdp.template'
    _OPTIONS: dict = {
        'protocol_whitelist': 'file,udp,rtp',
        'buffer_size': '4096',
        'stimeout': '1500000',
        'rw_timeout': '500000',
        'probesize': '1024',
        'analyzeduration': '0',
        'flags': 'low_delay',
        'fflags': 'nobuffer+discardcorrupt',
    }

    def __init__(
        self,
        host: str,
        port: int,
        payload_type: int,
        encoding_clock_chan: str,
        out_rate: int,
        out_channels: int,
        resampler_format: str,
        block_size: int,
        flush_partial_on_error: bool,
        **kwargs,
    ):
        """
        Parameters
        ----------
        host : str
            Listening host address.
        port : int
            Listening port.
        payload_type : int
            Type of the incoming packages.
        encoding_clock_chan : str
            encoding name/clock rate[/channels] for the RTP stream as defined
            in RFC 4566 (SDP) and in RFC 3555 (MIME type registration for RTP
            payload formats).
        out_rate : int
            Sampling rate of output audio.
        out_channels : int
            Audio channels of output chunks.
        resampler_format : str
            Output format of the audio resampler. Full list here:
            https://github.com/PyAV-Org/PyAV/blob/main/av/audio/frame.py#L16
        block_size : int
            Size of the audio block to sample, in seconds.
        flush_partial_on_error : bool
            Whether to flush the pending buffer when an error/close occurs.
            The emitted chunk will be padded to expected block size with zeros
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._host = host
        self._port = port
        self._payload_type = payload_type
        self._encoding_clock_chan = encoding_clock_chan
        self._out_rate = out_rate
        self._out_channels = out_channels
        self._block_size = block_size
        self._resampler_format = resampler_format
        self._flush_partial_on_error = flush_partial_on_error
        self._samples_per_block = int(self._out_rate * self._block_size)
        self._container = None
        self._resampler = None
        self._sdp_file_path = None

        self._t = None
        self._stop_event = threading.Event()

        self._abs_recv = 0
        self._elapsed = 0.0
        self._pending = np.empty((0,), dtype=np.float32)

    def configure(self):
        """Configure the node"""
        if self._port == 0:
            self._port = rb.get('port')

    def warmup(self):
        """Warmup the node"""
        self._sdp_file_path = self.sdp_descriptor
        self._t = threading.Thread(
            target=self._generate_chunks, args=(), daemon=True
        )

    def start(self):
        """Start the node"""
        self._t.start()
        super().start()

    def stop(self):
        """Stop the node"""
        self._stop_event.set()
        self._t.join()
        super().stop()

    def update(self, message: Message[AudioPayload]):
        """Receive data from upstream, transmit data downstream"""
        self.logger.debug('update method not implemented for source node')

    def _stream_audio_blocks(self):
        try:
            self._container = av.open(
                self.sdp_descriptor,
                options=self._OPTIONS,
                timeout=(None, JUTURNA_THREAD_JOIN_TIMEOUT),
            )
            self._stream = self._container.streams.audio[0]
            self._resampler = av.AudioResampler(
                format=self._resampler_format,
                layout='mono' if self._out_channels == 1 else 'stereo',
                rate=self._out_rate,
            )

            for packet in self._container.demux(self._stream):
                if self._stop_event.is_set():
                    break

                for raw_frame in packet.decode():
                    for frame in self._resampler.resample(raw_frame):
                        yield frame.to_ndarray()[0]

        except OSError:
            raise
        finally:
            if self._container:
                self._container.close()
                self._container = None

    def _flush_pending(self, force: bool = False):
        while len(self._pending) >= self._samples_per_block:
            chunk = self._pending[: self._samples_per_block]
            self._pending = self._pending[self._samples_per_block :]
            self._emit_chunk(chunk)

        if force and len(self._pending) > 0:
            self._emit_chunk(
                np.pad(
                    self._pending,
                    (0, self._samples_per_block - len(self._pending)),
                    mode='constant',
                )
            )

    def _generate_chunks(self):
        while not self._stop_event.is_set():
            try:
                for samples in self._stream_audio_blocks():
                    self._pending = np.concatenate([self._pending, samples])
                    self._flush_pending(force=False)

                    if self._stop_event.is_set():
                        break
            except av.error.ExitError:
                self.logger.debug(
                    f'demux terminate while reading {self._stop_event.is_set()}'
                )
            except OSError as e:
                if not self._stop_event.is_set():
                    self.logger.error(f'source unavailable ({e}), retrying...')
                    self._stop_event.wait(2.0)
            finally:
                self._flush_pending(force=self._flush_partial_on_error)
                self._pending = np.empty((0,), dtype=np.float32)
                self._elapsed = 0.0

    def _emit_chunk(self, audio: np.ndarray):
        chunk_duration = len(audio) / self._out_rate
        message = Message[AudioPayload](
            creator=self.name,
            version=self._abs_recv,
            payload=AudioPayload(
                audio=audio,
                sampling_rate=self._out_rate,
                channels=self._out_channels,
                audio_format=self._resampler_format,
                start=self._elapsed,
                end=self._elapsed + chunk_duration,
            ),
        )
        message.meta['size'] = message.payload.end - message.payload.start
        self._abs_recv += 1
        self._elapsed += chunk_duration
        self.transmit(message)

    @property
    def sdp_descriptor(self) -> pathlib.Path:
        """Fetch the SDP descriptor file"""
        return self._sdp_file_path or self.prepare_template(
            self._SDP_TEMPLATE_NAME,
            '_session_in.sdp',
            {
                '_remote_rtp_host': self._host,
                '_remote_rtp_port': self._port,
                '_remote_payload_type': self._payload_type,
                '_encoding_clock_chan': self._encoding_clock_chan,
            },
        )
