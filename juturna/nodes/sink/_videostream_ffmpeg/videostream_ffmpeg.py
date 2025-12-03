"""
VideostreamFFMPEG

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com

Transmit frames to a RTP endpoint through FFmpeg.
"""

import pathlib
import time
import subprocess

from juturna.components import Message
from juturna.components import Node

from juturna.payloads import ImagePayload


class VideostreamFFMPEG(Node[ImagePayload, None]):
    """Sink node for video streaming"""

    def __init__(
        self,
        dst_host: str,
        dst_port: int,
        in_width: int,
        in_height: int,
        out_width: int,
        out_height: int,
        gop: int,
        process_log_level: str,
        ffmpeg_proc_path: str,
        **kwargs,
    ):
        """
        Parameters
        ----------
        dst_host : str
            Hostname of the RTP endpoint to direct the stream to.
        dst_port : int
            Port of the RTP endpoint to direct the stream to.
        in_width : int
            Width of the incoming video data.
        in_height : int
            Height of the incoming video data.
        out_width : int
            Width of the outgoing video stream.
        out_height : int
            Height of the outgoing video stream.
        gop : int
            Interval at which send keyframes in the output stream.
        process_log_level : str
            Log level for the ffmpeg process.
        ffmpeg_proc_path : str
            Path to the ffmpeg launcher script template.
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._dst_host = dst_host
        self._dst_port = dst_port

        self._in_width = in_width
        self._in_height = in_height
        self._out_width = out_width
        self._out_height = out_height
        self._gop = gop
        self._ffmpeg_proc_path = ffmpeg_proc_path
        self._process_log_level = process_log_level

        self._ffmpeg_proc = None
        self._ffmpeg_launcher_path = None

    def warmup(self):
        """Warmup the node"""
        self._session_sdp_file = pathlib.Path(
            self.pipe_path, '_session_out.sdp'
        )

        self._ffmpeg_launcher_path = self.ffmpeg_launcher

    def start(self):
        """Start the node"""
        self._ffmpeg_proc = subprocess.Popen(
            ['sh', self.ffmpeg_launcher],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            bufsize=65536,
        )

        super().start()

    def stop(self):
        """Stop the node"""
        try:
            self._ffmpeg_proc.stdin.write('q\n')
            self._ffmpeg_proc.stdin.flush()
            self._ffmpeg_proc.stdin.close()

            time.sleep(2)

            self._ffmpeg_proc.terminate()
            self._ffmpeg_proc.wait()
            self._ffmpeg_proc = None
        except Exception:
            ...

    def update(self, message: Message[ImagePayload]):
        """Receive a message, transmit a message"""
        frame = message.payload.image
        frame_bytes = frame.tobytes()

        self._ffmpeg_proc.stdin.write(frame_bytes)
        self._ffmpeg_proc.stdin.flush()

    @property
    def ffmpeg_launcher(self) -> pathlib.Path:
        """Fetch the FFmpeg launcher script"""
        return self._ffmpeg_launcher_path or self.prepare_template(
            self._ffmpeg_proc_path,
            '_ffmpeg_launcher.sh',
            {
                '_in_frame_shape': f'{self._in_width}x{self._in_height}',
                '_out_frame_shape': f'{self._out_width}x{self._out_height}',
                '_dst_host': self._dst_host,
                '_dst_port': self._dst_port,
                '_gop': self._gop,
                '_process_log_level': self._process_log_level,
                '_sdp_file_path': self._session_sdp_file,
            },
        )
