import pathlib
import signal
import logging

import ffmpeg
import cv2

from juturna.components import Message
from juturna.components import BaseNode


class VideostreamFFMPEG(BaseNode):
    def __init__(self,
                 dst_host: str,
                 dst_port: int,
                 in_width: int,
                 in_height: int):
        super().__init__('sink')

        self._dst_host = dst_host
        self._dsp_port = dst_port

        self._width = in_width
        self._height = in_height

        self._ffmpeg_pipe = None
        self._ffmpeg_proc = None

    def warmup(self):
        session_sdp_file = pathlib.Path(
            self.pipe_path, '_out.sdp')

        self._ffmpeg_pipe = (
            ffmpeg
            .input('pipe:',
                   format='rawvideo',
                   pix_fmt='bgr24',
                   s=f'{self._width}x{self._height}')
            .output(f'rtp://{self._dst_host}:{self._dsp_port}',
                    format='rtp',
                    level='4.1',
                    pix_fmt='yuv420p',
                    preset='ultrafast',
                    g=25,
                    tune='zerolatency',
                    vcodec='libx264',
                    vprofile='baseline',
                    sdp_file=str(session_sdp_file))
            .overwrite_output()
        )

        logging.info(f'{self.name} ffmpeg out pipe prepared')

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
            logging.info('ffmpeg pipe not created')

    def update(self, message: Message):
        frame = message.payload
        frame = cv2.resize(frame, (self._width, self._height))

        self._ffmpeg_proc.stdin.write(frame.tobytes())
