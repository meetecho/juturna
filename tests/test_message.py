import time
import json

import numpy as np

from juturna.components import Message


def test_message_init():
    msg = Message()

    assert msg.created_at is not None
    assert msg.creator is None
    assert msg.version == -1
    assert msg.payload is None
    assert msg.meta == dict()
    assert msg.timers == dict()
    assert msg._current_timer is None


def test_message_init_with_params():
    msg = Message(creator='test_creator', version=1, payload='test_payload')

    assert msg.created_at is not None
    assert msg.creator == 'test_creator'
    assert msg.version == 1
    assert msg.payload == 'test_payload'
    assert msg.meta == dict()
    assert msg.timers == dict()
    assert msg._current_timer is None


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

    # measure time outside, compare with time inside
    start = time.time()
    with msg.timeit('test_timer'):
        time.sleep(2)
    elapsed = time.time() - start

    np.testing.assert_approx_equal(
        msg.timers['test_timer'], elapsed, significant=5
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
    msg.payload = np.array([1, 2, 3])

    json_str = msg.to_json(encoder=lambda x: x.tolist())

    assert isinstance(json_str, str)
    assert 'created_at' in json_str
    assert 'creator' in json_str
    assert 'version' in json_str
    assert 'payload' in json_str
    assert 'meta' in json_str
    assert 'timers' in json_str

    retrieved_payload = json.loads(json_str)['payload']

    assert isinstance(retrieved_payload, list)
    assert retrieved_payload == [1, 2, 3]
