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
                 audio_rate: int,
                 block_size: int,
                 payload_type: int,
                 channels: int,
                 rec_host: str,
                 trx_host: str):
        super().__init__('source')

        self._audio_rate = audio_rate
        self._block_size = block_size
        self._payload_type = payload_type
        self._channels = channels
        self._rec_thresh = self._audio_rate * self._block_size * 2 * 2
        self._abs_recv = 0

        self._rec_host = rec_host
        self._rec_port = None
        self._trx_host = trx_host
        self._trx_port = None

        self._data = bytearray()

        self._client = None
        self._local_stream_url = None

        self._ffmpeg_pipe = None
        self._ffmpeg_proc = None

    def configure(self):
        self._rec_port = rb.get('port')
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
        waveform = self._get_waveform(self._data[:self._rec_thresh])
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

    def prepare_local_sdp(self,sdp_file_template: str | pathlib.Path):
        session_sdp_file = str(pathlib.Path(self.session_path, '_session.sdp'))

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

    def _get_waveform(self, raw_data: bytearray) -> np.ndarray:
        waveform = np.frombuffer(
            raw_data, np.int16).flatten().astype(np.float32) / 32768.0

        if self._channels == 2:
            waveform = np.reshape(waveform, (-1, 2)).sum(axis=1) / 2

        return waveform

    @staticmethod
    def prepare_sdp(sdp_content: dict, template_location: str, dst: str):
        with open(template_location, 'r') as f:
            _sdp_template = f.read()

        _local_sdp = string.Template(_sdp_template).substitute(sdp_content)

        with open(dst, 'w') as f:
            f.write(_local_sdp)
