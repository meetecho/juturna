"""
Round-trips through `juturna.transport._browser`'s own wire format
(`_serialize_message`/`_deserialize_message`), the pickle-based transport
used between Workers - distinct from `_browser_io.py`, which only covers
the JSON-based format at the JS/Python edge (see `test_browser_io.py`).
"""

from juturna.components import Message
from juturna.payloads import AudioPayload
from juturna.payloads import ObjectPayload
from juturna.transport._browser import _deserialize_message
from juturna.transport._browser import _serialize_message


def _roundtrip(message: Message) -> Message:
    meta_bytes, dtype_code, ndim, shape, payload_buf = _serialize_message(
        message
    )
    shape_padded = (list(shape) + [0, 0, 0, 0])[:4]
    header = (
        len(meta_bytes),
        dtype_code,
        ndim,
        *shape_padded,
        len(payload_buf),
    )

    return _deserialize_message(header, meta_bytes, payload_buf)


def test_object_payload_roundtrip():
    message = Message(
        creator='src',
        payload=ObjectPayload(text='hi', language='en', start=0.0, end=1.0),
    )

    out = _roundtrip(message)

    assert isinstance(out.payload, ObjectPayload), (
        f'Expected ObjectPayload, got {type(out.payload).__name__}'
    )
    assert dict(out.payload) == dict(message.payload), (
        f'Expected {dict(message.payload)}, got {dict(out.payload)}'
    )


def test_object_payload_stays_frozen_after_roundtrip():
    message = Message(creator='src', payload=ObjectPayload(n=1))

    out = _roundtrip(message)

    try:
        out.payload['n'] = 2
        raise AssertionError('expected item assignment to be rejected')
    except TypeError:
        pass


def test_audio_payload_roundtrip_still_works():
    import numpy as np

    audio = np.linspace(-1, 1, 160, dtype=np.float32)
    message = Message(
        creator='src',
        payload=AudioPayload(
            audio=audio, sampling_rate=16000, channels=1, start=0.0, end=0.01
        ),
    )

    out = _roundtrip(message)

    assert np.array_equal(out.payload.audio, audio), 'audio samples changed'
