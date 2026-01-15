import time
import json
import dataclasses

import pytest
import numpy as np

from juturna.components import Message

from juturna.payloads._payloads import AudioPayload
from juturna.payloads._payloads import ImagePayload
from juturna.payloads._payloads import VideoPayload
from juturna.payloads._payloads import BytesPayload
from juturna.payloads._payloads import Batch
from juturna.payloads._payloads import ObjectPayload
from juturna.payloads._draft import Draft


def test_message_init():
    msg = Message()

    assert msg.created_at is not None
    assert msg.creator is None
    assert msg.version == -1
    assert msg.payload is None
    assert msg.meta == dict()
    assert msg.timers == dict()


def test_message_init_with_params():
    msg = Message(creator='test_creator', version=1, payload='test_payload')

    assert msg.created_at is not None
    assert msg.creator == 'test_creator'
    assert msg.version == 1
    assert msg.payload == 'test_payload'
    assert msg.meta == dict()
    assert msg.timers == dict()


def test_message_init_with_meta():
    msg = Message()

    msg.meta = {'key': 'value'}
    msg.meta['other_key'] = 'other_value'

    assert msg.meta == {'key': 'value', 'other_key': 'other_value'}


def test_message_init_with_timers():
    msg = Message()

    msg.timer('timer1', 1.0)
    msg.timer('timer2', 2.0)

    assert msg.timers == {'timer1': 1.0, 'timer2': 2.0}


def test_message_with_timer_copy():
    msg = Message()

    msg.timer('timer1', 1.0)
    msg.timer('timer2', 2.0)

    other_msg = Message(timers_from=msg)

    msg.timer('timer2', 3.0)
    other_msg.timer('timer3', 3.0)

    assert other_msg.timers['timer1'] == 1.0
    assert other_msg.timers['timer2'] == 2.0
    assert other_msg.timers['timer3'] == 3.0


def test_message_init_with_payload():
    msg = Message()

    msg.payload = {'key': 'value'}

    assert msg.payload == {'key': 'value'}


def test_message_timer_context():
    msg = Message()

    with msg.timeit('test_timer'):
        time.sleep(1)

    assert 'test_timer' in msg.timers
    assert msg.timers['test_timer'] > 0


def test_message_timer_duration():
    msg = Message()
    start = time.time()

    with msg.timeit('test_timer'):
        time.sleep(2)

    elapsed = time.time() - start

    assert int(msg.timers['test_timer']) == int(elapsed)

    np.testing.assert_approx_equal(
        msg.timers['test_timer'], elapsed, significant=3
    )


def test_message_duration_timer_reset():
    msg = Message()

    start = time.time()
    with msg.timeit('test_timer_1'):
        time.sleep(1)
    elapsed_1 = time.time() - start

    start = time.time()
    with msg.timeit('test_timer_2'):
        time.sleep(2)
    elapsed_2 = time.time() - start

    np.testing.assert_approx_equal(
        msg.timers['test_timer_1'], elapsed_1, significant=5
    )

    np.testing.assert_approx_equal(
        msg.timers['test_timer_2'], elapsed_2, significant=5
    )


def test_message_repr_string():
    msg = Message()

    assert str(msg) == '<Message from None, v. -1>'


def test_message_repr_dict():
    msg = Message()

    assert msg.to_dict() == {
        'created_at': msg.created_at,
        'creator': None,
        'version': -1,
        'payload': None,
        'meta': {},
        'timers': {},
    }


def test_message_to_json():
    msg = Message()

    json_str = msg.to_json()

    assert isinstance(json_str, str)
    assert 'created_at' in json_str
    assert 'creator' in json_str
    assert 'version' in json_str
    assert 'payload' in json_str
    assert 'meta' in json_str
    assert 'timers' in json_str


def test_message_to_json_custom_encoder():
    msg = Message()
    msg.payload = AudioPayload(audio=np.ndarray(10))

    json_str = msg.to_json(encoder=lambda x: 'custom_serialised')

    assert isinstance(json_str, str)
    assert 'created_at' in json_str
    assert 'creator' in json_str
    assert 'version' in json_str
    assert 'payload' in json_str
    assert 'meta' in json_str
    assert 'timers' in json_str

    recoded = json.loads(json_str)

    assert 'created_at' in recoded.keys()
    assert 'creator' in recoded.keys()
    assert 'version' in recoded.keys()
    assert 'payload' in recoded.keys()
    assert 'meta' in recoded.keys()
    assert 'timers' in recoded.keys()

    assert recoded['payload'] == 'custom_serialised'

def test_message_serialisation_audio():
    test_payload = AudioPayload(
        audio=np.asarray([1, 2, 3, 4, 5, 6, 7, 8, 9, 0]),
        sampling_rate=10,
        channels=2,
        audio_format='int32',
        start=0,
        end=5
    )

    test_message = Message(creator='tester', version=7, payload=test_payload)

    serialised = test_message.to_json()
    decoded = json.loads(serialised)

    assert isinstance(decoded['payload'], dict)
    assert isinstance(decoded['payload']['audio'], list)
    assert len(decoded['payload']['audio']) == 10
    assert decoded['payload']['audio'] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
    assert decoded['payload']['sampling_rate'] == 10
    assert decoded['payload']['channels'] == 2
    assert decoded['payload']['audio_format'] == 'int32'
    assert decoded['payload']['start'] == 0
    assert decoded['payload']['end'] == 5


def test_message_serialisation_image():
    test_payload = ImagePayload(
        image=np.ndarray((10, 10, 3)),
        width=10,
        height=10,
        depth=3,
        pixel_format='test_format',
        timestamp=111.11
    )

    test_message = Message(creator='tester', version=7, payload=test_payload)

    serialised = test_message.to_json()
    decoded = json.loads(serialised)

    assert isinstance(decoded['payload'], dict)
    assert isinstance(decoded['payload']['image'], list)
    assert len(decoded['payload']['image']) == 10
    assert decoded['payload']['width'] == 10
    assert decoded['payload']['height'] == 10
    assert decoded['payload']['depth'] == 3
    assert decoded['payload']['pixel_format'] == 'test_format'
    assert decoded['payload']['timestamp'] == 111.11


def test_message_freeze_modify_message():
    test_message = Message(creator='tester', version=10)

    test_message.freeze()

    with pytest.raises(TypeError) as context:
        test_message.creator = 'new_tester'

    assert 'frozen messages cannot be modified' in str(context.value)
    assert test_message.creator == 'tester'


def test_message_freeze_delete_message_attr():
    test_message = Message(creator='tester', version=10)

    test_message.freeze()

    with pytest.raises(TypeError) as context:
        del test_message.creator

    assert 'frozen messages cannot be modified' in str(context.value)
    assert test_message.creator == 'tester'


def test_message_freeze_meta():
    test_message = Message(creator='tester', version=10)

    test_message.meta['first_value'] = 10

    test_message.freeze()

    with pytest.raises(TypeError) as context:
        test_message.meta['first_value'] = 20

    assert "'mappingproxy' object does not support item assignment" in str(context.value)
    assert test_message.meta['first_value'] == 10


def test_message_freeze_timers():
    test_message = Message(creator='tester', version=10)

    test_message.freeze()

    with pytest.raises(TypeError) as context:
        with test_message.timeit('not_allowed'):
            time.sleep(1)

    assert 'frozen messages cannot be modified' in str(context.value)
    assert len(test_message.timers.keys()) == 0


def test_message_draft_payload():
    test_message = Message(
        creator='tester',
        version=7,
        payload=Draft(AudioPayload)
    )

    test_message.payload.sampling_rate = 1001
    test_message.payload.channels = 12

    test_message.freeze()

    assert isinstance(test_message.payload, AudioPayload)
    assert test_message.payload.sampling_rate == 1001
    assert test_message.payload.channels == 12


def test_message_draft_payload_object():
    test_message = Message(
        creator='tester',
        version=7,
        payload=Draft(ObjectPayload)
    )

    test_message.payload.first_key = 10
    test_message.payload.second_key = 'value'
    test_message.payload.third_key = False

    test_message.freeze()

    assert isinstance(test_message.payload, ObjectPayload)
    assert test_message.payload['first_key'] == 10
    assert test_message.payload['second_key'] == 'value'
    assert test_message.payload['third_key'] == False


def test_message_draft_payload_object_attr():
    test_message = Message(
        creator='tester',
        version=7,
        payload=Draft(ObjectPayload)
    )

    test_message.payload['first_key'] = 10
    test_message.payload['second_key'] = 'value'
    test_message.payload['third_key'] = False

    test_message.freeze()

    assert isinstance(test_message.payload, ObjectPayload)
    assert test_message.payload['first_key'] == 10
    assert test_message.payload['second_key'] == 'value'
    assert test_message.payload['third_key'] == False


def test_message_immutable_payload():
    test_payload = AudioPayload(
        audio=np.ndarray(10),
        sampling_rate=10,
        channels=2,
        start=0,
        end=5
    )

    test_message = Message(creator='tester', version=7, payload=test_payload)

    with pytest.raises(dataclasses.FrozenInstanceError) as context:
        test_message.payload.channels = 1

    assert "cannot assign to field 'channels'" in str(context.value)
    assert test_message.payload.channels == 2
