"""VideoRTP source node"""

import pathlib
import time
import subprocess

import numpy as np

from juturna.components import Message
from juturna.components import Node
from juturna.components import _resource_broker as rb

from juturna.payloads import BytesPayload, ImagePayload


class VideoRTP(Node[BytesPayload, ImagePayload]):
    """Source node for video streaming"""

    def __init__(
        self,
        rec_host: str,
        rec_port: int | str,
        payload_type: int,
        codec: str,
        width: int,
        height: int,
        **kwargs,
    ):
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
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._rec_host = rec_host
        self._rec_port = rec_port

        self._payload_type = payload_type
        self._codec = codec

        self._width = width
        self._height = height

        self._sdp_file_path = None
        self._ffmpeg_launcher_path = None
        self._ffmpeg_proc = None
        self._sent = 0

    def configure(self):
        """Configure the node"""
        if self._rec_port == 'auto':
            self._rec_port = rb.get('port')

    def warmup(self):
        """Warmup the node"""
        self._sdp_file_path = self.sdp_descriptor
        self._ffmpeg_launcher_path = self.ffmpeg_launcher

    def start(self):
        """Start the node"""
        self._ffmpeg_proc = subprocess.Popen(
            ['sh', self.ffmpeg_launcher],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            bufsize=10**8,
        )

        self.set_source(
            lambda: Message[BytesPayload](
                creator=self.name,
                payload=BytesPayload(
                    cnt=self._ffmpeg_proc.stdout.read(  # type: ignore
                        self._width * self._height * 3
                    )
                ),
            )
        )

        super().start()

    def stop(self):
        """Stop the node"""
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
        except Exception:
            ...

        super().stop()

    def destroy(self):
        """Destroy the node"""
        self.stop()

    @property
    def configuration(self) -> dict:
        """Fetch node configuration"""
        base_config = super().configuration
        base_config['port'] = self._rec_port

        return base_config

    def update(self, message: Message[BytesPayload]):
        """Receive a message, transmit a message"""
        try:
            full_frame = np.frombuffer(message.payload.cnt, np.uint8).reshape(
                (self._height, self._width, 3)
            )

            to_send = Message[ImagePayload](
                creator=self.name,
                version=self._sent,
                payload=ImagePayload(
                    image=full_frame,
                    width=full_frame.shape[0],
                    height=full_frame.shape[1],
                    pixel_format='rgb24',
                    timestamp=time.time(),
                ),
            )

            self.transmit(to_send)
            self._sent += 1
        except Exception as _:
            ...

    @property
    def sdp_descriptor(self) -> pathlib.Path:
        """Fetch the SDP descriptor file"""
        return self._sdp_file_path or self.prepare_template(
            'remote_source.sdp.template',
            '_session_in.sdp',
            {
                '_remote_rtp_host': self._rec_host,
                '_remote_rtp_port': self._rec_port,
                '_remote_codec': self._codec,
                '_remote_payload_type': self._payload_type,
            },
        )

    @property
    def ffmpeg_launcher(self) -> pathlib.Path:
        """Fetch the FFmpeg launcher script"""
        return self._ffmpeg_launcher_path or self.prepare_template(
            'ffmpeg_launcher.sh.template',
            '_ffmpeg_launcher.sh',
            {
                '_sdp_location': self.sdp_descriptor,
                '_frame_shape': f'{self._width}x{self._height}',
            },
        )
