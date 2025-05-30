import string
import pathlib
import signal
import logging

import ffmpeg
import numpy as np

from juturna.components import _resource_broker as rb
from juturna.components import Message
from juturna.components import BaseNode

from juturna.utils.net_utils import RTPClient


class AudioRTP(BaseNode):
    """Source node for streaming audio
    """
    def __init__(self,
                 rec_host: str,
                 trx_host: str,
                 rec_port: int | str,
                 trx_port: int | str,
                 audio_rate: int,
                 block_size: int,
                 channels: int,
                 payload_type: int):
        """
        Parameters
        ----------
        rec_host : str
            Hostname of the remote RTP server to receive audio from.
        trx_host : str
            Hostname of the local RTP server to transmit audio to.
        rec_port : int | str
            Port of the RTP server to receive audio from. If set to "auto",
            the port will be assigned automatically by the resource broker.
        trx_port : int | str
            Port of the local RTP server to transmit audio to. If set to "auto",
            the port will be assigned automatically by the resource broker.
        audio_rate : int
            Audio sample rate in Hz (samples per seconds).
        block_size : int
            Size of the audio block to sample, in seconds.
        channels : int
            Number of source audio channels.
        payload_type : int
            Payload type for the RTP stream.
        """
        super().__init__('source')

        self._audio_rate = audio_rate
        self._block_size = block_size
        self._payload_type = payload_type
        self._channels = channels
        self._rec_thresh = self._audio_rate * self._block_size * 2 * 2
        self._abs_recv = 0

        self._rec_host = rec_host
        self._rec_port = rec_port
        self._trx_host = trx_host
        self._trx_port = trx_port

        self._data = bytearray()

        self._client = None
        self._local_stream_url = None

        self._ffmpeg_pipe = None
        self._ffmpeg_proc = None

    def configure(self):
        if self._rec_port == 'auto':
            self._rec_port = rb.get('port')

        if self._trx_port == 'auto':
            self._trx_port = rb.get('port')

        self._client = RTPClient(self._trx_host, self._trx_port)
        self._local_stream_url = f'rtp://{self._trx_host}:{self._trx_port}'
        logging.info(f'local stream on {self._local_stream_url}')

        self.set_source(lambda: self._client.rec(self._audio_rate))

        logging.info(f'[{self.name}] listening on port {self._rec_port}')

    def warmup(self):
        mod_location = self.static_path
        sdp_file_template = pathlib.Path(
            mod_location, 'local_source.sdp.template')

        self._ffmpeg_pipe = self.prepare_local_sdp(sdp_file_template)
        logging.info('ffmpeg pipe created')
        logging.info(self._ffmpeg_pipe)

    def start(self):
        if self._ffmpeg_proc is None:
            self._ffmpeg_proc = self._ffmpeg_pipe.run_async(pipe_stdin=True)

        logging.info('ffmpeg proc')
        logging.info(self._ffmpeg_proc)

        self._client.connect()
        super().start()

    def destroy(self):
        self._client.disconnect()
        self.stop()

        try:
            self._ffmpeg_proc.send_signal(signal.SIGINT)

            self._ffmpeg_pipe = None
            self._ffmpeg_proc = None
        except Exception:
            logging.info('ffmpeg pipe not created')

    @property
    def configuration(self) -> dict:
        base_config = BaseNode.configuration.fget(self)
        base_config['port'] = self._rec_port

        return base_config

    def update(self, new_data):
        self._data += new_data.payload

        if len(self._data) < self._rec_thresh:
            return

        logging.info(f'{self.name} receive: {self._abs_recv}')
        waveform = AudioRTP._get_waveform(self._data[:self._rec_thresh],
                                          self._channels)
        message = Message(
            creator=self.name,
            payload=waveform,
            version=self._abs_recv)

        message.meta['size'] = self._block_size
        message.meta['source_recv'] = self._abs_recv

        self.transmit(message)
        logging.info(f'{self.name} transmit: {self._abs_recv}')

        self._data = bytearray()
        self._abs_recv += 1

    def prepare_local_sdp(
        self, sdp_file_template: str | pathlib.Path) -> ffmpeg.input:
        session_sdp_file = str(pathlib.Path(self.pipe_path, '_session.sdp'))

        sdp_content = {
            '_remote_rtp_host': self._rec_host,
            '_remote_rtp_port': self._rec_port,
            '_remote_payload_type': self._payload_type}

        AudioRTP.prepare_sdp(
            sdp_content,
            sdp_file_template,
            session_sdp_file)

        ffmpeg_pipe = (
            ffmpeg
            .input(session_sdp_file, protocol_whitelist='file,rtp,udp')
            .output(self._local_stream_url,
                    format='rtp',
                    ac=self._channels,
                    acodec='pcm_s16le',
                    ar=self._audio_rate,
                    loglevel='quiet'))

        return ffmpeg_pipe

    @staticmethod
    def _get_waveform(raw_data: bytearray, channels: int) -> np.ndarray:
        waveform = np.frombuffer(
            raw_data, np.int16).flatten().astype(np.float32) / 32768.0

        if channels == 2:
            waveform = np.reshape(waveform, (-1, 2)).sum(axis=1) / 2

        return waveform

    @staticmethod
    def prepare_sdp(sdp_content: dict, template_location: str, dst: str):
        with open(template_location, 'r') as f:
            _sdp_template = f.read()

        _local_sdp = string.Template(_sdp_template).substitute(sdp_content)

        with open(dst, 'w') as f:
            f.write(_local_sdp)
