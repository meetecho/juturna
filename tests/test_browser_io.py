import numpy as np
import pytest

from juturna.components import Message
from juturna.payloads import AudioPayload, BytesPayload, ImagePayload
from juturna.payloads import ObjectPayload
from juturna.transport._browser_io import decode_message, encode_message


def _roundtrip(message):
    return decode_message(encode_message(message), creator='in')


def test_audio_roundtrip():
    audio = np.linspace(-1, 1, 1600, dtype=np.float32)
    message = Message(
        creator='src',
        payload=AudioPayload(
            audio=audio, sampling_rate=16000, channels=1, start=0.0, end=0.1
        ),
    )
    message.meta['session_id'] = 'abc'

    out = _roundtrip(message)

    assert isinstance(out.payload, AudioPayload), (
        f'Expected AudioPayload, got {type(out.payload).__name__}'
    )
    assert np.array_equal(out.payload.audio, audio), 'audio samples changed'
    assert out.payload.sampling_rate == 16000, (
        f'Expected 16000, got {out.payload.sampling_rate}'
    )
    assert out.meta == {'session_id': 'abc'}, f'Unexpected meta: {out.meta}'


def test_int16_audio_is_normalised():
    raw = np.array([0, 16384, -32768], dtype=np.int16)

    out = decode_message(
        {'kind': 'audio', 'payload': {'audio': raw, 'sampling_rate': 8000}},
        creator='in',
    )

    expected = np.array([0.0, 0.5, -1.0], dtype=np.float32)
    assert np.array_equal(out.payload.audio, expected), (
        f'Expected {expected}, got {out.payload.audio}'
    )


def test_image_is_reshaped():
    image = np.arange(4 * 3 * 4, dtype=np.uint8).reshape(3, 4, 4)
    message = Message(
        creator='src',
        payload=ImagePayload(
            image=image, width=4, height=3, depth=4, pixel_format='rgba'
        ),
    )

    encoded = encode_message(message)
    assert encoded['payload']['image'].ndim == 1, 'image must be sent flat'

    out = decode_message(encoded, creator='in')
    assert out.payload.image.shape == (3, 4, 4), (
        f'Expected (3, 4, 4), got {out.payload.image.shape}'
    )
    assert np.array_equal(out.payload.image, image), 'pixels changed'


def test_bytes_and_object_roundtrip():
    out = _roundtrip(Message(creator='s', payload=BytesPayload(cnt=b'\x00\x01')))
    assert out.payload.cnt == b'\x00\x01', f'Unexpected bytes: {out.payload.cnt}'

    out = _roundtrip(
        Message(creator='s', payload=ObjectPayload(text='hi', n=3))
    )
    assert dict(out.payload) == {'text': 'hi', 'n': 3}, (
        f'Unexpected object: {dict(out.payload)}'
    )


def test_invalid_messages_are_rejected():
    with pytest.raises(ValueError, match='unknown message kind'):
        decode_message({'kind': 'video', 'payload': {}}, creator='in')

    with pytest.raises(ValueError, match='unknown audio payload fields'):
        decode_message(
            {'kind': 'audio', 'payload': {'samples': []}}, creator='in'
        )

    with pytest.raises(TypeError, match='unsupported payload'):
        encode_message(Message(creator='s', payload=object()))


def test_frozen_message_keeps_its_meta():
    message = Message(
        creator='s',
        payload=AudioPayload(audio=np.zeros(4, dtype=np.float32)),
    )
    message.meta['i'] = 3
    message._freeze()

    encoded = encode_message(message)

    assert encoded['meta'] == {'i': 3}, (
        f'Expected the meta of the message, got {encoded["meta"]!r}'
    )
