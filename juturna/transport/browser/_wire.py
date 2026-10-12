import json
import pickle

from typing import Any

# the shape of an array takes 4 of those words: that is its most dimensions
_MAX_NDIM = 4

_DTYPE_CODES = {
    'uint8': 1,
    'float32': 2,
    'int16': 3,
    'float64': 4,
    'int32': 5,
}

_DTYPE_BY_CODE = {code: name for name, code in _DTYPE_CODES.items()}

_KIND_IMAGE = 'image'
_KIND_AUDIO = 'audio'
_KIND_BYTES = 'bytes'
_KIND_PICKLE = 'pickle'

DEFAULT_QUEUE_CAPACITY = 8
DEFAULT_MAX_META_JSON_BYTES = 4096
DEFAULT_MAX_PAYLOAD_BYTES = 2_000_000  # above one 1080p uint8 frame


def _serialize_message(msg) -> tuple[bytes, int, int, tuple[int, ...], Any]:
    """
    Return (meta_json_bytes, dtype_code, ndim, shape, payload_buf).

    dtype_code 0 means the payload is not an array: payload_buf is then raw
    bytes (pickled for the fallback path).
    """
    import numpy as np

    from juturna.payloads import AudioPayload
    from juturna.payloads import BytesPayload
    from juturna.payloads import ImagePayload

    payload = msg.payload

    meta = {
        'id': msg.id,
        'created_at': msg.created_at,
        'creator': msg.creator,
        'version': msg.version,
        'meta': dict(msg.meta),
        'timers': dict(msg.timers),
        'data_source_id': msg._data_source_id,
    }

    if isinstance(payload, ImagePayload):
        arr = payload.image
        meta['kind'] = _KIND_IMAGE
        meta['payload_meta'] = {
            'width': payload.width,
            'height': payload.height,
            'depth': payload.depth,
            'pixel_format': payload.pixel_format,
            'timestamp': payload.timestamp,
        }
        dtype_code, ndim, shape, payload_buf = _array_wire(arr, np)

        return (
            json.dumps(meta).encode('utf-8'),
            dtype_code,
            ndim,
            shape,
            payload_buf,
        )

    if isinstance(payload, AudioPayload):
        arr = payload.audio
        meta['kind'] = _KIND_AUDIO
        meta['payload_meta'] = {
            'sampling_rate': payload.sampling_rate,
            'audio_format': payload.audio_format,
            'channels': payload.channels,
            'start': payload.start,
            'end': payload.end,
        }
        dtype_code, ndim, shape, payload_buf = _array_wire(arr, np)

        return (
            json.dumps(meta).encode('utf-8'),
            dtype_code,
            ndim,
            shape,
            payload_buf,
        )

    if isinstance(payload, BytesPayload):
        meta['kind'] = _KIND_BYTES
        meta['payload_meta'] = {}
        payload_buf = payload.cnt

        return (
            json.dumps(meta).encode('utf-8'),
            _DTYPE_CODES['uint8'],
            1,
            (len(payload_buf),),
            payload_buf,
        )

    # VideoPayload, Batch, ObjectPayload, or any custom payload type: no
    # known binary layout, fall back to pickle. Correct,
    # not on the fast path - Buffer._consume() emits Batch for multi-input
    # nodes, so this is a real path, not a hypothetical.
    meta['kind'] = _KIND_PICKLE
    meta['payload_meta'] = {}
    payload_buf = pickle.dumps(payload)

    return json.dumps(meta).encode('utf-8'), 0, 0, (), payload_buf


def _deserialize_message(header, meta_json_bytes: bytes, payload_bytes):
    import numpy as np

    from juturna.components._message import Message
    from juturna.payloads import AudioPayload
    from juturna.payloads import BytesPayload
    from juturna.payloads import ImagePayload

    meta_json_len, dtype_code, ndim, s0, s1, s2, s3, payload_len = (
        int(x) for x in header[:8]
    )
    shape = tuple(int(x) for x in (s0, s1, s2, s3)[:ndim])

    meta = json.loads(meta_json_bytes[:meta_json_len].decode('utf-8'))
    kind = meta['kind']
    pm = meta['payload_meta']
    raw = bytes(payload_bytes[:payload_len])

    if kind in (_KIND_IMAGE, _KIND_AUDIO):
        arr = np.frombuffer(raw, dtype=_DTYPE_BY_CODE[dtype_code]).reshape(
            shape
        )
        payload = (
            ImagePayload(image=arr, **pm)
            if kind == _KIND_IMAGE
            else AudioPayload(audio=arr, **pm)
        )
    elif kind == _KIND_BYTES:
        payload = BytesPayload(cnt=raw)
    elif kind == _KIND_PICKLE:
        payload = pickle.loads(raw)
    else:
        raise ValueError(f'unknown payload kind on wire: {kind!r}')

    msg = Message(
        creator=meta['creator'], version=meta['version'], payload=payload
    )
    msg.id = meta['id']
    msg.created_at = meta['created_at']
    msg.meta = dict(meta['meta'])
    msg.timers = dict(meta['timers'])
    msg._data_source_id = meta['data_source_id']
    msg._freeze()

    return msg


def _array_wire(arr, np) -> tuple[int, int, tuple[int, ...], Any]:
    dtype_code = _DTYPE_CODES.get(str(arr.dtype))

    if dtype_code is None:
        raise ValueError(
            f'unsupported array dtype for BrowserTransport: {arr.dtype!r} '
            f'(supported: {sorted(_DTYPE_CODES)})'
        )

    if arr.ndim > _MAX_NDIM:
        raise ValueError(
            f'unsupported array for BrowserTransport: {arr.ndim} dimensions, '
            f'at most {_MAX_NDIM} fit in a queue slot'
        )

    # a reinterpretation, not a conversion: a uint8 destination view would
    # otherwise corrupt float32 audio
    flat_bytes = arr.reshape(-1).view(np.uint8)

    return dtype_code, len(arr.shape), tuple(arr.shape), flat_bytes
