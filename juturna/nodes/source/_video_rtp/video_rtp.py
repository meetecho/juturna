import signal
import string
import pathlib
import time

import ffmpeg
import numpy as np

from juturna.components import Message
from juturna.components import BaseNode
from juturna.components import _resource_broker as rb


class VideoRTP(BaseNode):
    """Source node for video streaming
    """
    def __init__(self,
                 rec_host: str,
                 rec_port: int | str,
                 payload_type: int,
                 codec: str,
                 width: int,
                 height: int):
        """
        Parameters
        ----------
        rec_host : str
            Hostname of the remote RTP stream to receive video from.
        rec_port : int | str
            Port of the RTP stream to receive video from. If set to "auto",
            the port will be assigned automatically by the resource broker.
        payload_type : int
            Payload type for the RTP stream.
        codec : str
            The codec used from the remote video source.
        width : int
            Width of the received RTP video stream.
        height : int
            Height of the received RTP video stream.
        """
        super().__init__('source')

        self._rec_host = rec_host
        self._rec_port = rec_port

        self._payload_type = payload_type
        self._codec = codec

        self._width = width
        self._height = height

        self._ffmpeg_pipe = None
        self._ffmpeg_proc = None
        self._sdp_file_path = None
        self._sent = 0

    def configure(self):
        if self._rec_port == 'auto':
            self._rec_port = rb.get('port')

    def warmup(self):
        self._ffmpeg_pipe = (
            ffmpeg
            .input(self.sdp_descriptor, protocol_whitelist='file,rtp,udp')
            .output('pipe:',
                    s=f'{self._width}x{self._height}',
                    format='rawvideo',
                    pix_fmt='rgb24',
                    loglevel='quiet'))

    def start(self):
        self._ffmpeg_proc = self._ffmpeg_pipe.run_async(
            pipe_stdin=True, pipe_stdout=True)

        self.set_source(lambda: self._ffmpeg_proc.stdout.read(
            self._width * self._height * 3))

        super().start()

    def stop(self):
        try:
            self._ffmpeg_proc.terminate()
            time.sleep(2)
            self._ffmpeg_proc.send_signal(signal.SIGINT)

            self._ffmpeg_pipe = None
            self._ffmpeg_proc = None
        except Exception:
            ...

        super().stop()

    def destroy(self):
        self.stop()

    def update(self, frame):
        try:
            full_frame = np.frombuffer(frame, np.uint8).reshape(
                (self._height, self._width, 3))
            to_send = Message(creator=self.name, version=self._sent)
            to_send.payload = full_frame

            self.transmit(to_send)
            self._sent += 1
        except Exception as _:
            ...

    @property
    def sdp_descriptor(self) -> pathlib.Path:
        if self._sdp_file_path:
            return self._sdp_file_path

        sdp_file_template = pathlib.Path(
            self.static_path, 'remote_source.sdp.template')

        session_sdp_file = pathlib.Path(
            self.pipe_path, '_session_in.sdp')

        sdp_content = {
            '_remote_rtp_host': self._rec_host,
            '_remote_rtp_port': self._rec_port,
            '_remote_codec': self._codec,
            '_remote_payload_type': self._payload_type
        }

        with open(sdp_file_template, 'r') as f:
            _sdp_template = f.read()

        _local_sdp = string.Template(_sdp_template).substitute(sdp_content)

        with open(session_sdp_file, 'w') as f:
            f.write(_local_sdp)

        self._sdp_file_path = session_sdp_file.resolve()

        return self._sdp_file_path
