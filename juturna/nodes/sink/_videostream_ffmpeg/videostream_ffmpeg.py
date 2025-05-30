import pathlib
import signal

import ffmpeg
import cv2

from juturna.components import Message
from juturna.components import BaseNode


class VideostreamFFMPEG(BaseNode):
    """Sink node for video streaming
    """
    def __init__(self,
                 dst_host: str,
                 dst_port: int,
                 in_width: int,
                 in_height: int,
                 framerate: int,
                 gop: int):
        """
        Parameters
        ----------
        dst_host : str
            Hostname of the RTP endpoint to direct the stream to.
        dst_port : int
            Port of the RTP endpoint to direct the stream to.
        in_width : int
            Width of the video stream to send to the endpoint.
        in_height : int
            Height of the video stream to send to the endpoint.
        framerate : int
            Frames per second of the output video stream.
        gop : int
            Interval at which send keyframes in the output stream.
        """
        super().__init__('sink')

        self._dst_host = dst_host
        self._dsp_port = dst_port

        self._width = in_width
        self._height = in_height
        self._framerate = framerate
        self._gop = gop

        self._ffmpeg_pipe = None
        self._ffmpeg_proc = None

    def warmup(self):
        session_sdp_file = pathlib.Path(
            self.pipe_path, '_session_out.sdp')

        self._ffmpeg_pipe = (
            ffmpeg
            .input('pipe:',
                   format='rawvideo',
                   pix_fmt='rgb24',
                   s=f'{self._width}x{self._height}')
            .output(f'rtp://{self._dst_host}:{self._dsp_port}',
                    level='3.1',
                    pix_fmt='yuv420p',
                    preset='ultrafast',
                    framerate=self._framerate,
                    g=self._gop,
                    tune='zerolatency',
                    vcodec='libx264',
                    vprofile='baseline',
                    format='rtp',
                    loglevel='quiet',
                    sdp_file=str(session_sdp_file))
            .overwrite_output()
        )

    def start(self):
        self._ffmpeg_proc = self._ffmpeg_pipe.run_async(pipe_stdin=True)

        super().start()

    def destroy(self):
        self.stop()

        try:
            self._ffmpeg_proc.send_signal(signal.SIGINT)

            self._ffmpeg_pipe = None
            self._ffmpeg_proc = None
        except Exception:
            ...

    def update(self, message: Message):
        frame = message.payload
        frame = cv2.resize(frame, (self._width, self._height))

        self._ffmpeg_proc.stdin.write(frame.tobytes())
