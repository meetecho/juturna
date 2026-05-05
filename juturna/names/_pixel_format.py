from enum import StrEnum
from enum import unique


@unique
class PixelFormat(StrEnum):
    """
    Supported pixel formats for image and video payloads.
    - RGB / BGR (24-bit):
      ``RGB24``, ``BGR24``
    - RGBA (32-bit with alpha):
      ``RGBA``, ``ARGB``, ``BGRA``, ``ABGR``
    - YUV planar / packed:
      ``YUV420P``, ``YUV444P``, ``YUYV422``, ``NV12``, ``NV21``
    - Grayscale:
      ``GRAY``, ``GRAY8``
    - Other:
      ``PAL8``, ``GBRP``
    """

    # RGB / BGR (24-bit)
    RGB24 = 'rgb24'
    BGR24 = 'bgr24'

    # RGBA (32-bit with alpha)
    RGBA = 'rgba'
    ARGB = 'argb'
    BGRA = 'bgra'
    ABGR = 'abgr'

    # YUV planar / packed
    YUV420P = 'yuv420p'
    YUV444P = 'yuv444p'
    YUYV422 = 'yuyv422'
    NV12 = 'nv12'
    NV21 = 'nv21'

    # Grayscale
    GRAY = 'gray'
    GRAY8 = 'gray8'

    # Other
    PAL8 = 'pal8'
    GBRP = 'gbrp'

    @property
    def is_rgb(self) -> bool:
        """Return ``True`` if the format is RGB-ordered."""
        match self:
            case (
                PixelFormat.RGB24
                | PixelFormat.RGBA
                | PixelFormat.ARGB
            ):
                return True
            case _:
                return False

    @property
    def is_bgr(self) -> bool:
        """Return ``True`` if the format is BGR-ordered."""
        match self:
            case (
                PixelFormat.BGR24
                | PixelFormat.BGRA
                | PixelFormat.ABGR
            ):
                return True
            case _:
                return False

    @property
    def has_alpha(self) -> bool:
        """Return ``True`` if the format has an alpha channel."""
        match self:
            case (
                PixelFormat.RGBA
                | PixelFormat.ARGB
                | PixelFormat.BGRA
                | PixelFormat.ABGR
            ):
                return True
            case _:
                return False

    @property
    def is_yuv(self) -> bool:
        """Return ``True`` if the format is a YUV variant."""
        match self:
            case (
                PixelFormat.YUV420P
                | PixelFormat.YUV444P
                | PixelFormat.YUYV422
                | PixelFormat.NV12
                | PixelFormat.NV21
            ):
                return True
            case _:
                return False

    @property
    def is_grayscale(self) -> bool:
        """Return ``True`` if the format is grayscale."""
        match self:
            case PixelFormat.GRAY | PixelFormat.GRAY8:
                return True
            case _:
                return False
