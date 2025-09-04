import pathlib
import subprocess
import threading
import time
import logging

import numpy as np

from juturna.components import _resource_broker as rb
from juturna.components import Message
from juturna.components import BaseNode
from juturna.payloads import BytesPayload, AudioPayload
from juturna.names import ComponentStatus


class AudioRTP(BaseNode[BytesPayload, AudioPayload]):
    """Source node for streaming audio
    """
    _SDP_TEMPLATE_NAME : str = 'remote_source.sdp.template'
    _FFMPEG_TEMPLATE_NAME : str = 'ffmpeg_launcher.sh.template'

    def __init__(self,
                 rec_host: str,
                 rec_port: int | str,
                 audio_rate: int,
                 block_size: int,
                 channels: int,
                 payload_type: int):
        """
        Parameters
        ----------
        rec_host : str
            Hostname of the remote RTP server to receive audio from.
        rec_port : int | str
            Port of the RTP server to receive audio from. If set to "auto",
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
        self._rec_bytes = np.dtype(np.int16).itemsize * \
            self._channels * \
            self._block_size * \
            self._audio_rate
        self._abs_recv = 0

        self._rec_host = rec_host
        self._rec_port = rec_port

        self._sdp_file_path = None
        self._ffmpeg_proc = None
        self._ffmpeg_launcher_path = None
        self._monitor_thread = None

    def configure(self):
        if self._rec_port == 'auto':
            self._rec_port = rb.get('port')

    def warmup(self):
        self._sdp_file_path = self.sdp_descriptor
        self._ffmpeg_launcher_path = self.ffmpeg_launcher

    def start(self):
        self._ffmpeg_proc = subprocess.Popen(
            ['sh', self.ffmpeg_launcher],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=64536)

        self._monitor_thread = threading.Thread(target=self.monitor_process, args=(self._ffmpeg_proc,))
        self._monitor_thread.start()

        self.set_source(lambda: Message[BytesPayload](
            creator=self.name,
            payload=BytesPayload(
                cnt=self._ffmpeg_proc.stdout.read(self._rec_bytes)))) # type: ignore

        super().start()

    def stop(self):
        try:
            assert self._ffmpeg_proc is not None
            assert self._ffmpeg_proc.stdin is not None

            self._ffmpeg_proc.stdin.write(b'q\n')
            self._ffmpeg_proc.stdin.flush()
            self._ffmpeg_proc.stdin.close()

            time.sleep(2)

            self._ffmpeg_proc.terminate()
            self._ffmpeg_proc.wait()
            self._ffmpeg_proc = None

            self._monitor_thread.join()

        except Exception:
            ...

        super().stop()

    def destroy(self):
        self.stop()

    @property
    def configuration(self) -> dict:
        base_config = super().configuration
        base_config['port'] = self._rec_port

        return base_config

    def update(self, message: Message[BytesPayload]):
        waveform = AudioRTP._get_waveform(message.payload.cnt, self._channels)

        to_send = Message[AudioPayload](
            creator=self.name,
            version=self._abs_recv,
            payload=AudioPayload(
                audio=waveform,
                sampling_rate=self._audio_rate,
                channels=self._channels,
                start=self._block_size * self._abs_recv,
                end=self._block_size * self._abs_recv + self._block_size
            ))

        to_send.meta['size'] = self._block_size
        to_send.meta['source_recv'] = self._abs_recv

        self.transmit(to_send)

        self._abs_recv += 1

    @staticmethod
    def _get_waveform(raw_data: bytes, channels: int) -> np.ndarray:
        waveform = np.frombuffer(
            raw_data, np.int16).flatten().astype(np.float32) / 32768.0

        if channels == 2:
            waveform = np.reshape(waveform, (-1, 2)).sum(axis=1) / 2

        return waveform

    @property
    def sdp_descriptor(self) -> pathlib.Path:
        return self._sdp_file_path or \
            self.prepare_template(
                AudioRTP._SDP_TEMPLATE_NAME, '_session_in.sdp', {
                    '_remote_rtp_host': self._rec_host,
                    '_remote_rtp_port': self._rec_port,
                    '_remote_payload_type': self._payload_type })

    @property
    def ffmpeg_launcher(self) -> pathlib.Path:
        return self._ffmpeg_launcher_path or \
            self.prepare_template(
                AudioRTP._FFMPEG_TEMPLATE_NAME, '_ffmpeg_launcher.sh', {
                    '_sdp_location': self.sdp_descriptor,
                    '_audio_rate': self._audio_rate })

    def monitor_process(self, proc):
        proc.wait()
        self.clear_source()
        logging.debug(f'{self.name} subprocess terminates with code: {proc.returncode} - current node status: {self.status.name}')
        time.sleep(5)
        if self.status == ComponentStatus.RUNNING:
            logging.info(f'{self.name} subprocess is respawning in 5 seconds')
            self.stop()
            time.sleep(5)
            self.start()
