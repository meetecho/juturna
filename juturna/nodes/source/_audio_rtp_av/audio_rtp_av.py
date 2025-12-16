"""
AudioRtpAv

@author: Antonio Bevilacqua
@email: b3by.in.th3.sky@gmail.com
@created_at: 2025-12-16 21:54:39

Consume RTP audio streams using PyAv.
"""

import typing
import threading
import pathlib

import av
import numpy as np

from juturna.components import Node
from juturna.components import Message

from juturna.payloads import AudioPayload
from juturna.components import _resource_broker as rb


class AudioRtpAv(Node[AudioPayload, AudioPayload]):
    """Node implementation class"""

    _SDP_TEMPLATE_NAME: str = 'remote_source.sdp.template'
    _OPTIONS: dict = {
        'protocol_whitelist': 'file,udp,rtp',
        'buffer_size': '4096',
        'stimeout': '1500000',
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
        in_rate: int,
        out_rate: int,
        in_channels: int,
        out_channels: int,
        block_size: int,
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
        in_rate : int
            Sampling rate of incoming audio.
        out_rate : int
            Sampling rate of output audio.
        in_channels : int
            Audio channels of incoming stream.
        out_channels : int
            Audio channels of output chunks.
        block_size : int
            Size of the audio block to sample, in seconds.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._host = host
        self._port = port
        self._payload_type = payload_type
        self._encoding_clock_chan = encoding_clock_chan
        self._in_rate = in_rate
        self._out_rate = out_rate
        self._in_channels = in_channels
        self._out_channels = out_channels
        self._block_size = block_size

        self._samples_per_block = int(self._out_rate * self._block_size)
        self._container = None
        self._resampler = None
        self._fifo = None
        self._sdp_file_path = None

        self._t = None
        self._stop_event = threading.Event()
        self._abs_recv = 0

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

    def set_on_config(self, prop: str, value: typing.Any):
        """Hot-swap node properties"""
        ...

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
        message.meta['size'] = self._block_size

        self.transmit(message)

    def _stream_audio_blocks(self):
        self._container = None

        try:
            self._container = av.open(
                self.sdp_descriptor, options=self._OPTIONS
            )
            self._stream = self._container.streams.audio[0]

            self._fifo = av.audio.fifo.AudioFifo()
            self._resampler = av.AudioResampler(
                format='s16' if self._out_channels == 1 else 's16p',
                layout='mono' if self._out_channels == 1 else 'stereo',
                rate=self._out_rate,
            )

            for packet in self._container.demux(self._stream):
                if self._stop_event.is_set():
                    break

                for raw_frame in packet.decode():
                    for frame in self._resampler.resample(raw_frame):
                        frame.pts = None
                        self._fifo.write(frame)

                        while self._fifo.samples >= self._samples_per_block:
                            yield self._fifo.read(self._samples_per_block)
        finally:
            if self._container:
                self._container.close()

    def _generate_chunks(self):
        while not self._stop_event.is_set():
            try:
                for chunk in self._stream_audio_blocks():
                    if self._stop_event.is_set():
                        break

                    audio_data = chunk.to_ndarray().astype(np.float32) / 32768.0

                    self.put(
                        Message[AudioPayload](
                            creator=self.name,
                            version=self._abs_recv,
                            payload=AudioPayload(
                                audio=audio_data,
                                sampling_rate=self._out_rate,
                                channels=self._out_channels,
                                start=self._block_size * self._abs_recv,
                                end=self._block_size * (self._abs_recv + 1),
                            ),
                        )
                    )

                    self._abs_recv += 1

            except OSError as e:
                if not self._stop_event.is_set():
                    self.logger.info(f'source unavailable ({e}), retrying...')
                    self._stop_event.wait(2.0)

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
