import copy
import dataclasses
import json
import pickle

import pytest

import numpy as np

import juturna as jt
import juturna.meta as meta

from juturna.components import Message
from juturna.payloads import _payloads

from juturna.payloads._payloads import AudioPayload
from juturna.payloads._payloads import ImagePayload
from juturna.payloads._payloads import VideoPayload
from juturna.payloads._payloads import BytesPayload
from juturna.payloads._payloads import ObjectPayload
from juturna.payloads._payloads import BasePayload
from juturna.payloads._payloads import Batch

from juturna.payloads._draft import Draft


def test_audio_empty_init():
    payload = AudioPayload()

    np.testing.assert_array_equal(payload.audio, np.ndarray(0))

    assert payload.sampling_rate == -1
    assert payload.channels == -1
    assert payload.start == -1
    assert payload.end == -1


def test_image_empty_init():
    payload = ImagePayload()

    np.testing.assert_array_equal(payload.image, np.ndarray([0, 0]))

    assert payload.width == -1
    assert payload.height == -1
    assert payload.pixel_format == ''
    assert payload.timestamp == -1.0


def test_video_empty_init():
    payload = VideoPayload()

    assert payload.video == tuple()
    assert payload.frames_per_second == -1.0
    assert payload.start == -1.0
    assert payload.end == -1.0


def test_bytes_empty_init():
    payload = BytesPayload()

    assert payload.cnt == bytes()


def test_clone_payload():
    original = np.ndarray(10)

    first = AudioPayload(audio=original)
    cloned = first.clone()

    np.testing.assert_array_equal(first.audio, cloned.audio)

    assert id(first.audio) != id(cloned.audio)


def test_object_payload():
    origin = {'prop_a': 'string', 'prop_b': 10}

    payload = ObjectPayload.from_dict(origin)

    assert payload['prop_a'] == 'string'
    assert payload['prop_b'] == 10


def test_serialize_audio():
    test_waveform = [1, 2, 3, 4, 5]
    test_audio = np.asarray(test_waveform, dtype=np.int8)

    test_payload = AudioPayload(
        audio=test_audio,
        sampling_rate=100,
        channels=1,
        start=0,
        end=5
    )

    serialized = AudioPayload.serialize(test_payload)

    assert isinstance(serialized, dict)
    assert serialized['audio'] == test_waveform
    assert serialized['sampling_rate'] == 100
    assert serialized['channels'] == 1
    assert serialized['start'] == 0
    assert serialized['end'] == 5


def test_serialize_image():
    test_frame = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    test_image = np.asarray(test_frame, dtype=np.float32)

    test_payload = ImagePayload(
        image=test_image,
        width=3,
        height=3,
        depth=1,
        pixel_format='test_format'
    )

    serialized = ImagePayload.serialize(test_payload)

    assert isinstance(serialized, dict)
    np.testing.assert_array_equal(serialized['image'], test_image)
    assert serialized['width'] == 3
    assert serialized['height'] == 3
    assert serialized['depth'] == 1
    assert serialized['pixel_format'] == 'test_format'


def test_payload_draft():
    test_draft = Draft(ImagePayload)

    test_draft.image = np.ndarray((3, 2, 3))
    test_draft.width = 3
    test_draft.height = 2
    test_draft.depth = 3
    test_draft.pixel_format = 'test_format'

    test_payload = test_draft.compile()

    assert isinstance(test_payload, ImagePayload)


def test_immutable_object_payload_draft():
    test_draft = Draft(ObjectPayload)

    test_draft.prop_a = 'value'
    test_draft.prop_b = 10

    test_payload = test_draft.compile()

    with pytest.raises(TypeError) as context:
        test_payload['prop_c'] = 20

    assert "'ObjectPayload' object does not support item assignment" in str(context.value)


def test_draft_invalid_fields():
    test_draft = Draft(AudioPayload)

    with pytest.raises(AttributeError) as context:
        test_draft.invalid_field = 10

    assert 'invalid_field not allowed in AudioPayload' in str(context.value)


def test_draft_copy_from():
    pl = AudioPayload(channels=11, sampling_rate=11_000)
    test_draft = Draft(AudioPayload, copy_from=pl)

    assert test_draft.channels == 11
    assert test_draft.sampling_rate == 11_000

    test_payload = test_draft.compile()

    assert test_payload.channels == 11
    assert test_payload.sampling_rate == 11_000


def test_draft_copy_from_object():
    test_content = ObjectPayload(prop_a=10, prop_b='value')
    test_draft = Draft(ObjectPayload, copy_from=test_content)

    assert test_draft.prop_a == 10
    assert test_draft.prop_b == 'value'

    test_payload = test_draft.compile()

    assert test_payload['prop_a'] == 10
    assert test_payload.prop_b == 'value'

@pytest.mark.parametrize(
    'mutate',
    [
        lambda p: p.update(prop_c=30),
        lambda p: p.update({'prop_a': 0}),
        lambda p: p.pop('prop_a'),
        lambda p: p.pop('missing', None),
        lambda p: p.popitem(),
        lambda p: p.clear(),
        lambda p: p.setdefault('prop_c', 30),
        lambda p: p.__setitem__('prop_a', 0),
        lambda p: p.__delitem__('prop_a'),
        lambda p: p.__ior__({'prop_c': 30}),
    ],
    ids=[
        'update_kwargs',
        'update_dict',
        'pop',
        'pop_default',
        'popitem',
        'clear',
        'setdefault',
        'setitem',
        'delitem',
        'ior',
    ],
)
def test_object_payload_rejects_every_mutator(mutate):
    payload = ObjectPayload(prop_a=10, prop_b='value')

    with pytest.raises(TypeError, match="'ObjectPayload' object does not"):
        mutate(payload)

    assert payload == {'prop_a': 10, 'prop_b': 'value'}


def test_object_payload_in_place_or_is_rejected():
    payload = ObjectPayload(prop_a=10)
    alias = payload

    with pytest.raises(TypeError):
        alias |= {'prop_b': 20}

    assert payload == {'prop_a': 10}


def test_object_payload_or_returns_a_new_dict():
    payload = ObjectPayload(prop_a=10)
    merged = payload | {'prop_b': 20}

    assert merged == {'prop_a': 10, 'prop_b': 20}
    assert payload == {'prop_a': 10}


def test_object_payload_copies_keep_working():
    payload = ObjectPayload(prop_a=[1, 2], prop_b='value')

    assert pickle.loads(pickle.dumps(payload)) == payload
    assert copy.deepcopy(payload) == payload
    assert payload.clone() == payload


def test_object_payload_size_is_computed_on_first_access(monkeypatch):
    calls = list()
    real_deep_size = _payloads._deep_size

    def counting_deep_size(obj, max_visits):
        calls.append(obj)

        return real_deep_size(obj, max_visits)

    monkeypatch.setattr(_payloads, '_deep_size', counting_deep_size)

    payload = ObjectPayload(prop_a=np.zeros(1000, dtype=np.uint8))

    assert calls == []

    first = payload.size_bytes
    second = payload.size_bytes

    assert first == second
    assert len(calls) == 1


def test_object_payload_size_counts_nested_values():
    audio = AudioPayload(audio=np.zeros(100, dtype=np.float32))
    payload = ObjectPayload(
        mask=np.zeros((10, 100), dtype=np.uint8),
        audio=audio,
        boxes=[{'xyxy': [1, 2, 3, 4]} for _ in range(10)],
    )

    # the mask buffer and the audio payload, plus the containers
    assert payload.size_bytes > 1000 + audio.size_bytes
    assert payload.size_bytes > ObjectPayload(
        mask=np.zeros((10, 100), dtype=np.uint8), audio=audio
    ).size_bytes


def test_object_payload_size_counts_shared_values_once():
    frame = np.zeros(10_000, dtype=np.uint8)

    once = ObjectPayload(a=frame)
    twice = ObjectPayload(a=frame, b=frame)

    assert twice.size_bytes - once.size_bytes < frame.nbytes


def test_object_payload_size_handles_cycles():
    loop = list()
    loop.append(loop)

    assert ObjectPayload(loop=loop).size_bytes > 0


def test_object_payload_size_walk_is_bounded(monkeypatch):
    rows = [{'a': i, 'b': [i] * 10} for i in range(1000)]

    full = ObjectPayload(rows=rows).size_bytes

    monkeypatch.setattr(meta, 'JUTURNA_PAYLOAD_SIZE_MAX_VISITS', 50)
    bounded = ObjectPayload(rows=rows).size_bytes

    assert 0 < bounded < full


class _TelemetrySink:
    def __init__(self):
        self.batches = list()

    def record_telemetry(self, batch: list):
        self.batches.append(batch)


def test_object_payload_size_is_not_computed_without_telemetry():
    node = jt.components.Node(node_name='idle', pipe_name='p')
    payload = ObjectPayload(prop_a=np.zeros(1000, dtype=np.uint8))

    node._rec_telemetry(Message(creator='src', payload=payload), 'rx')

    assert 'size_bytes' not in vars(payload)

    node.link_telemetry(_TelemetrySink())
    node._rec_telemetry(Message(creator='src', payload=payload), 'rx')

    assert 'size_bytes' in vars(payload)
    assert node._telemetry_buffer[-1][-1] == payload.size_bytes


def _frame(value=1):
    return ImagePayload(image=np.full((2, 2, 3), value, dtype=np.uint8))


def test_video_payload_holds_frames():
    frames = [_frame(1), _frame(2)]
    payload = VideoPayload(video=frames)

    frames.append(_frame(3))

    assert payload.video == tuple(frames[:2])
    assert payload.size_bytes == 24


def test_video_payload_serializes_its_frames():
    payload = VideoPayload(video=[_frame(7)], codec='raw')

    serialized = VideoPayload.serialize(payload)

    assert serialized['codec'] == 'raw'
    assert serialized['video'] == [ImagePayload.serialize(_frame(7))]


@pytest.mark.parametrize('payload_type', [AudioPayload, ObjectPayload])
def test_draft_clear_removes_every_value(payload_type):
    draft = Draft(payload_type)
    draft['start' if payload_type is AudioPayload else 'key'] = 1.0

    draft.clear()

    assert draft._draft == {}
    assert isinstance(draft.compile(), payload_type)


@pytest.mark.parametrize(
    'make',
    [lambda: Draft(AudioPayload), lambda: ObjectPayload(a=1)],
    ids=['draft', 'object_payload'],
)
def test_missing_attribute_raises_attribute_error(make):
    item = make()

    with pytest.raises(AttributeError, match='missing'):
        item.missing

    assert not hasattr(item, 'missing')
    assert getattr(item, 'missing', 'default') == 'default'


def test_draft_can_be_copied_and_pickled():
    draft = Draft(AudioPayload)
    draft.sampling_rate = 16000

    for copied in (copy.deepcopy(draft), pickle.loads(pickle.dumps(draft))):
        assert copied.sampling_rate == 16000
        assert copied.compile().sampling_rate == 16000


@dataclasses.dataclass(frozen=True)
class _Detection(BasePayload):
    label: str = ''
    mask: np.ndarray = dataclasses.field(
        default_factory=lambda: np.zeros(2, dtype=np.uint8)
    )
    raw: bytes = b''
    crop: ImagePayload = dataclasses.field(default_factory=ImagePayload)
    boxes: tuple = ()
    extra: ObjectPayload = dataclasses.field(default_factory=ObjectPayload)


def test_custom_payload_serializes_by_default():
    payload = _Detection(
        label='cat',
        raw=b'\x00\x01',
        crop=_frame(5),
        boxes=((1, 2), (3, 4)),
        extra=ObjectPayload(score=np.ones(2, dtype=np.uint8)),
    )

    dumped = json.loads(Message(creator='src', payload=payload).to_json())

    assert dumped['payload'] == {
        'label': 'cat',
        'mask': [0, 0],
        'raw': 'AAE=',
        'crop': ImagePayload.serialize(_frame(5)),
        'boxes': [[1, 2], [3, 4]],
        'extra': {'score': [1, 1]},
    }


def test_non_dataclass_payload_serialization_names_the_class():
    class Plain(AudioPayload):
        pass

    with pytest.raises(TypeError, match='Plain is not a dataclass'):
        BasePayload.serialize(Plain())


@pytest.mark.parametrize(
    'make',
    [
        lambda: AudioPayload(audio=np.zeros(10)),
        _frame,
        lambda: VideoPayload(video=[_frame(), _frame()]),
        lambda: BytesPayload(cnt=b'abcd'),
        lambda: Batch(messages=(Message(creator='a', payload=_frame()),)),
    ],
    ids=['audio', 'image', 'video', 'bytes', 'batch'],
)
@pytest.mark.parametrize(
    'duplicate',
    [
        lambda p: pickle.loads(pickle.dumps(p)),
        copy.deepcopy,
        lambda p: p.clone(),
    ],
    ids=['pickle', 'deepcopy', 'clone'],
)
def test_size_bytes_survives_copies(make, duplicate):
    payload = make()

    assert duplicate(payload).size_bytes == payload.size_bytes > 0
