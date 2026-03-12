class PixelFormat:
    @staticmethod
    def _normalize_format(fmt: str) -> str:
        return fmt.strip().lower()

    __slots__ = ['RGB', 'BGR', 'RGB24', 'BGR24', 'RGBA', 'ARGB', 'BGRA', 'ABGR', 'YUV420P', 'YUV444P', 'YUYV422', 'GRAY', 'GRAY8', 'PAL8', 'GBRP']

    RGB = 'rgb'
    BGR = 'bgr'

    RGB24 = 'rgb24'
    BGR24 = 'bgr24'

    RGBA = 'rgba'
    ARGB = 'argb'
    BGRA = 'bgra'
    ABGR = 'abgr'

    YUV420P = 'yuv420p'
    YUV444P = 'yuv444p'
    YUYV422 = 'yuyv422'

    GRAY = 'gray'
    GRAY8 = 'gray8'

    PAL8 = 'pal8'
    GBRP = 'gbrp'
