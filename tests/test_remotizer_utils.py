import numpy as np
import pytest

from juturna.components import Message
from juturna.payloads import (
    AudioPayload,
    Batch,
    BytesPayload,
    ImagePayload,
    ObjectPayload,
    VideoPayload,
)

pytest.importorskip('google.protobuf')

from juturna.remotizer.utils import (  # noqa: E402
    deserialize_message,
    from_typed_value,
    message_to_proto,
    to_typed_value,
)


def _round_trip(message: Message) -> Message:
    return deserialize_message(message_to_proto(message))


def _image(depth: int) -> ImagePayload:
    shape = (2, 3) if depth == 1 else (2, 3, depth)

    return ImagePayload(
        image=np.arange(np.prod(shape), dtype=np.uint8).reshape(shape),
        width=3,
        height=2,
        depth=depth,
        pixel_format='gray' if depth == 1 else 'rgb24',
        timestamp=1.5,
    )


def test_typed_values_keep_their_types():
    value = {
        'none': None,
        'flag': True,
        'count': 3,
        'big': 2**62,
        'ratio': 1.0,
        'text': 'ciao',
        'raw': b'\x00\xff',
        'items': [1, (2, 3)],
        'tags': frozenset({'a', 'b'}),
        1: {'nested': [None]},
        'array': np.arange(6, dtype=np.int16).reshape(2, 3),
        'scalar': np.float32(0.5),
        'empty': ([], (), {}),
    }

    back = from_typed_value(to_typed_value(value))

    assert back.keys() == value.keys()

    for key in ('none', 'flag', 'count', 'big', 'ratio', 'text', 'raw'):
        assert type(back[key]) is type(value[key]), f'{key}: {back[key]!r}'
        assert back[key] == value[key]

    assert back['items'] == [1, (2, 3)] and type(back['items'][1]) is tuple
    assert back['tags'] == frozenset({'a', 'b'})
    assert back[1] == {'nested': [None]}
    assert back['array'].dtype == np.int16
    assert np.array_equal(back['array'], value['array'])
    assert back['array'].flags.writeable
    assert type(back['scalar']) is np.float32 and back['scalar'] == 0.5
    assert back['empty'] == ([], (), {})


def test_unsupported_values_are_refused():
    with pytest.raises(TypeError, match='a set cannot be sent'):
        to_typed_value({'ids': {1, 2}})


def test_meta_keeps_its_types():
    message = Message(creator='src', payload=BytesPayload(cnt=b'x'))
    message.meta.update(
        seq=3,
        score=0.5,
        span=(1, 2),
        token=b'\x01',
        origin={'room': 'a', 'ids': [1, 2]},
        mask=np.array([True, False]),
    )
    message._freeze()

    meta = _round_trip(message).meta

    assert meta['seq'] == 3 and type(meta['seq']) is int
    assert meta['score'] == 0.5
    assert meta['span'] == (1, 2)
    assert meta['token'] == b'\x01'
    assert meta['origin'] == {'room': 'a', 'ids': (1, 2)}, meta['origin']
    assert np.array_equal(meta['mask'], [True, False])


def test_meta_with_unsupported_values_is_refused():
    message = Message(creator='src', payload=BytesPayload(cnt=b'x'))
    message.meta['ids'] = {1, 2}

    with pytest.raises(TypeError, match='a set cannot be sent'):
        message_to_proto(message)


@pytest.mark.parametrize(
    'payload',
    [
        AudioPayload(
            audio=np.arange(8, dtype=np.float32).reshape(4, 2),
            sampling_rate=16000,
            audio_format='f32le',
            channels=2,
            start=1.0,
            end=1.25,
        ),
        _image(1),
        _image(3),
        VideoPayload(
            video=(_image(3), _image(3)),
            frames_per_second=25.0,
            codec='raw',
            start=0.0,
            end=0.08,
        ),
        BytesPayload(cnt=b'\x00\x01'),
    ],
    ids=['audio', 'gray_image', 'rgb_image', 'video', 'bytes'],
)
def test_payloads_survive_the_round_trip(payload):
    message = Message(creator='src', version=4, payload=payload)
    back = _round_trip(message)

    assert type(back.payload) is type(payload)
    assert back.version == 4

    for name, value in vars(payload).items():
        got = getattr(back.payload, name)

        if isinstance(value, np.ndarray):
            assert got.dtype == value.dtype and np.array_equal(got, value)
        elif name == 'video':
            assert type(got) is tuple and len(got) == len(value)
            assert all(np.array_equal(g.image, v.image) for g, v in zip(got, value))
        else:
            assert got == value, f'{name}: {got!r} != {value!r}'


def test_object_payload_keeps_its_types():
    payload = ObjectPayload(text='ciao', n=3, scores=[0.5, 1], span=(1, 2))

    back = _round_trip(Message(creator='asr', payload=payload)).payload

    assert type(back) is ObjectPayload
    assert dict(back) == {
        'text': 'ciao',
        'n': 3,
        'scores': [0.5, 1],
        'span': (1, 2),
    }
    assert type(back['n']) is int and type(back['scores'][1]) is int


def test_batch_messages_come_back_as_messages():
    inner = Message(creator='mic', version=7, payload=BytesPayload(cnt=b'a'))
    inner.meta['seq'] = 7
    inner._freeze()

    back = _round_trip(Message(creator='agg', payload=Batch(messages=(inner,))))
    (item,) = back.payload.messages

    assert type(item) is Message
    assert item.version == 7 and item.meta['seq'] == 7
    assert item.payload.cnt == b'a'


def test_messages_inside_a_value_come_back_frozen():
    message = Message(creator='src', payload=BytesPayload(cnt=b'a'))
    message._freeze()

    back = from_typed_value(to_typed_value({'last': message}))['last']

    assert back._is_frozen
    assert back.payload.cnt == b'a'


def test_values_that_cannot_be_sent_can_be_left_out():
    dropped = list()
    value = {'keep': [1, {2}, 3], 'ids': {1}, frozenset({1}): 'key', 'n': 1}

    back = from_typed_value(to_typed_value(value, dropped, 'state'))

    assert back == {'keep': [1, 3], frozenset({1}): 'key', 'n': 1}
    assert dropped == ["state['keep'][1] (set)", "state['ids'] (set)"]


def test_object_arrays_cannot_be_sent():
    value = {'ok': np.arange(2), 'objects': np.array([{1}, None])}
    dropped = list()

    back = from_typed_value(to_typed_value(value, dropped, 'state'))

    assert list(back) == ['ok'], back
    assert dropped == ["state['objects'] (ndarray)"]

    with pytest.raises(TypeError, match='ndarray cannot be sent'):
        to_typed_value(value)


def test_messages_can_leave_out_what_cannot_be_sent():
    inner = Message(creator='mic', payload=ObjectPayload(ok=1, ids={1}))
    inner.meta['seq'] = 1
    message = Message(creator='agg', payload=Batch(messages=(inner,)))
    message.meta.update(origin='x', ids={2})
    dropped = list()

    back = deserialize_message(message_to_proto(message, dropped))

    assert dict(back.meta) == {'origin': 'x'}
    assert dict(back.payload.messages[0].payload) == {'ok': 1}
    assert dropped == [
        "message.meta['ids'] (set)",
        "message.payload[0].payload['ids'] (set)",
    ]
