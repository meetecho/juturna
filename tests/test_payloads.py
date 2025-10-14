import numpy as np

from juturna.payloads._payloads import AudioPayload
from juturna.payloads._payloads import ImagePayload
from juturna.payloads._payloads import VideoPayload
from juturna.payloads._payloads import BytesPayload
from juturna.payloads._payloads import ObjectPayload


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

    assert payload.video == list()
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
