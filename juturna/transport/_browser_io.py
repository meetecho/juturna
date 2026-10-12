"""
Wire format between a web page and the browser-only I/O nodes.

A message crosses the page/Worker boundary as a plain JS object::

    {kind, payload, meta, creator, id, created_at}

``kind`` is one of ``audio``, ``image``, ``bytes`` or ``object`` and
``payload`` carries the fields of the matching payload dataclass. Arrays are
sent flat (``Float32Array``, ``Uint8Array``, ...) and rebuilt from the other
fields on arrival: an image is reshaped to ``(height, width, depth)``.

``encode_message``/``decode_message`` are plain Python and can be used (and
tested) outside Pyodide; ``message_to_js``/``message_from_js`` only add the
conversion to and from JS objects, which needs Pyodide.
"""

import dataclasses
import json

import numpy as np

from juturna.components._message import Message
from juturna.payloads import AudioPayload
from juturna.payloads import BytesPayload
from juturna.payloads import ImagePayload
from juturna.payloads import ObjectPayload

_KINDS = {
    'audio': AudioPayload,
    'image': ImagePayload,
    'bytes': BytesPayload,
    'object': ObjectPayload,
}


def encode_message(message: Message) -> dict:
    """
    Turn a message into a dict of JSON-compatible values and flat arrays.

    Raises
    ------
    TypeError
        If the payload type has no browser representation.

    """
    payload = message.payload
    kind = next(
        (name for name, cls in _KINDS.items() if isinstance(payload, cls)),
        None,
    )

    if kind is None:
        raise TypeError(
            f'unsupported payload for the browser: {type(payload).__name__}'
        )

    if kind == 'object':
        fields = json.loads(json.dumps(dict(payload), default=str))
    else:
        fields = {
            f.name: getattr(payload, f.name)
            for f in dataclasses.fields(payload)
        }
        fields = {
            name: np.ascontiguousarray(value).reshape(-1)
            if isinstance(value, np.ndarray)
            else value
            for name, value in fields.items()
        }

    return {
        'kind': kind,
        'payload': fields,
        'meta': json.loads(json.dumps(dict(message.meta), default=str)),
        'creator': message.creator,
        'id': message.id,
        'created_at': message.created_at,
    }


def decode_message(data: dict, creator: str) -> Message:
    """
    Build a message from the dict produced by a page (or `encode_message`).

    Raises
    ------
    ValueError
        If ``kind`` is unknown or the payload has unexpected fields.

    """
    kind = data.get('kind')
    cls = _KINDS.get(kind)

    if cls is None:
        raise ValueError(
            f'unknown message kind {kind!r}, expected one of {sorted(_KINDS)}'
        )

    fields = dict(data.get('payload') or {})

    if kind == 'object':
        payload = ObjectPayload(**fields)
    else:
        known = {f.name for f in dataclasses.fields(cls)}

        if unknown := set(fields) - known:
            raise ValueError(
                f'unknown {kind} payload fields: {sorted(unknown)}'
            )

        if 'audio' in fields:
            fields['audio'] = _as_audio(fields['audio'])

        if 'image' in fields:
            fields['image'] = _as_image(fields['image'], fields)

        if 'cnt' in fields:
            fields['cnt'] = bytes(fields['cnt'])

        payload = cls(**fields)

    message = Message(creator=creator, payload=payload)
    message.meta.update(data.get('meta') or {})

    return message


def message_to_js(message: Message):
    """Encode a message as a JS object (Pyodide only)."""
    from js import Object
    from pyodide.ffi import to_js

    return to_js(encode_message(message), dict_converter=Object.fromEntries)


def message_from_js(js_message, creator: str) -> Message:
    """Decode a JS object sent by the page (Pyodide only)."""
    return decode_message(js_message.to_py(), creator)


def _as_audio(buffer) -> np.ndarray:
    array = np.array(buffer)

    if array.dtype == np.int16:
        return array.astype(np.float32) / 32768.0

    return array.astype(np.float32, copy=False)


def _as_image(buffer, fields: dict) -> np.ndarray:
    array = np.array(buffer)
    shape = (fields.get('height', -1), fields.get('width', -1))
    shape += (fields.get('depth', -1),)

    if min(shape) > 0 and array.size == int(np.prod(shape)):
        return array.reshape(shape)

    return array
