"""
Utility functions for converting between Python objects and Protobuf messages.

This module provides helper functions to:
- Convert internal `juturna.components.Message` and its Payloads
  to their corresponding Protobuf representations in `protos/payloads.proto`.
- Deserialize `ProtoMessage` and `ProtoPayload` back into Python objects.
- Create/deserialize `ProtoEnvelope` for wrapping messages in the wire protocol.

These utilities are essential for the serialization layer of the Remotizer.
"""

import numpy as np
import uuid
import time
from typing import Any


from juturna.components import Message
from juturna.components._message import _FrozenDict
from juturna.payloads import (
    AudioPayload,
    ImagePayload,
    VideoPayload,
    BytesPayload,
    ObjectPayload,
    Batch,
)

from juturna.remotizer.c_protos.payloads_pb2 import (
    ProtoMessage,
    ProtoEnvelope,
    AudioProtoPayload,
    ImageProtoPayload,
    VideoProtoPayload,
    BytesProtoPayload,
    ObjectProtoPayload,
    BatchProto,
    TypedValue,
)
from google.protobuf.json_format import MessageToDict


# ============================================================================
# PYTHON → PROTOBUF CONVERTERS
# ============================================================================


def _audio_to_proto(audio: AudioPayload) -> AudioProtoPayload:
    """Convert Python AudioPayload to Protobuf AudioProtoPayload"""
    proto = AudioProtoPayload()

    # Convert numpy array to bytes
    proto.audio_data = audio.audio.tobytes()
    proto.dtype = str(audio.audio.dtype)
    proto.shape.extend(audio.audio.shape)

    # Copy metadata
    proto.sampling_rate = audio.sampling_rate
    proto.channels = audio.channels
    proto.audio_format = audio.audio_format
    proto.start = audio.start
    proto.end = audio.end

    return proto


def _image_to_proto(image: ImagePayload) -> ImageProtoPayload:
    """Convert Python ImagePayload to Protobuf ImageProtoPayload"""
    proto = ImageProtoPayload()

    # Convert numpy array to bytes
    proto.image_data = image.image.tobytes()
    proto.dtype = str(image.image.dtype)

    # Copy metadata
    proto.width = image.width
    proto.height = image.height
    proto.depth = image.depth
    proto.pixel_format = image.pixel_format
    proto.timestamp = image.timestamp

    return proto


def _video_to_proto(video: VideoPayload) -> VideoProtoPayload:
    """Convert Python VideoPayload to Protobuf VideoProtoPayload"""
    proto = VideoProtoPayload()

    # Convert each frame
    for frame in video.video:
        frame_proto = _image_to_proto(frame)
        proto.frames.append(frame_proto)

    # Copy metadata
    proto.frames_per_second = video.frames_per_second
    proto.start = video.start
    proto.codec = video.codec
    proto.end = video.end

    return proto


def _bytes_to_proto(bytes_payload: BytesPayload) -> BytesProtoPayload:
    """Convert Python BytesPayload to Protobuf BytesProtoPayload"""
    proto = BytesProtoPayload()
    proto.cnt = bytes_payload.cnt
    proto.size = len(bytes_payload.cnt)
    return proto


def _object_to_proto(
    obj: ObjectPayload, dropped: list[str] | None = None, path: str = 'payload'
) -> ObjectProtoPayload:
    """Convert Python ObjectPayload (dict) to Protobuf ObjectProtoPayload"""
    proto = ObjectProtoPayload()
    proto.data.CopyFrom(to_typed_value(dict(obj), dropped, path))

    return proto


def _batch_to_proto(
    batch: Batch, dropped: list[str] | None = None, path: str = 'payload'
) -> BatchProto:
    """Convert Python Batch to Protobuf BatchProto"""
    proto = BatchProto()
    for index, message in enumerate(batch.messages):
        message_proto = message_to_proto(message, dropped, f'{path}[{index}]')
        proto.messages.append(message_proto)
    return proto


PROTOBUF_PAYLOAD_TYPE_MAP = {
    AudioPayload: _audio_to_proto,
    ImagePayload: _image_to_proto,
    VideoPayload: _video_to_proto,
    BytesPayload: _bytes_to_proto,
    ObjectPayload: _object_to_proto,
    Batch: _batch_to_proto,
}


def message_to_proto(
    message: Message, dropped: list[str] | None = None, path: str = 'message'
) -> ProtoMessage:
    """
    Convert Python Message to Protobuf ProtoMessage

    Handles all payload types:
    - AudioPayload → AudioProtoPayload
    - ImagePayload → ImageProtoPayload
    - VideoPayload → VideoProtoPayload
    - BytesPayload → BytesProtoPayload
    - ObjectPayload → ObjectProtoPayload
    - Batch → BatchProto

    Parameters
    ----------
    message : Message
        Python Message object with any payload type
    dropped : list[str] | None
        None to refuse meta and object payload values that cannot be sent,
        or a list collecting the paths of the ones left out (see
        to_typed_value).
    path : str
        Name of the message, used in those paths.

    Returns
    -------
    ProtoMessage
        Protobuf message ready for serialization

    """
    proto = ProtoMessage()

    proto.created_at = message.created_at
    proto.creator = message.creator
    proto.version = message.version
    proto.id = message.id

    proto.meta.CopyFrom(
        to_typed_value(dict(message.meta), dropped, f'{path}.meta')
    )
    proto.timers.update(dict(message.timers))

    if message.payload is not None:
        protocol_converter = PROTOBUF_PAYLOAD_TYPE_MAP.get(
            type(message.payload)
        )

        # only these payloads hold values that may not be sent
        if protocol_converter in (_object_to_proto, _batch_to_proto):
            payload_proto = protocol_converter(
                message.payload, dropped, f'{path}.payload'
            )
        else:
            payload_proto = protocol_converter(message.payload)

        proto.payload.Pack(payload_proto)
    return proto


# ============================================================================
# PROTOBUF →  PYTHON CONVERTERS
# ============================================================================


def deserialize_message(message: ProtoMessage) -> Message:
    """
    Convert Protobuf ProtoMessage to Python Message

    Automatically unpacks and converts the payload based on its type:
    - AudioProtoPayload → AudioPayload
    - ImageProtoPayload → ImagePayload
    - VideoProtoPayload → VideoPayload
    - BytesProtoPayload → BytesPayload
    - ObjectProtoPayload → ObjectPayload
    - BatchProto → Batch

    Parameters
    ----------
    message : ProtoMessage
        Protobuf message to convert

    Returns
    -------
    Message
        Python Message object with appropriate payload type

    """
    message_obj = Message(
        creator=message.creator,
        version=message.version,
        payload=None,  # to be filled below
    )
    message_obj.created_at = message.created_at
    if message.HasField('meta'):
        message_obj.meta.update(from_typed_value(message.meta))

    message_obj.timers.update(dict(message.timers))
    message_obj.id = message.id

    if message.payload.Is(AudioProtoPayload.DESCRIPTOR):
        audio = AudioProtoPayload()
        message.payload.Unpack(audio)
        message_obj.payload = _deserialize_audio_payload(audio)

    elif message.payload.Is(ImageProtoPayload.DESCRIPTOR):
        image = ImageProtoPayload()
        message.payload.Unpack(image)
        message_obj.payload = _deserialize_image_payload(image)

    elif message.payload.Is(VideoProtoPayload.DESCRIPTOR):
        video = VideoProtoPayload()
        message.payload.Unpack(video)
        message_obj.payload = _deserialize_video_payload(video)

    elif message.payload.Is(BytesProtoPayload.DESCRIPTOR):
        bytes_payload = BytesProtoPayload()
        message.payload.Unpack(bytes_payload)
        message_obj.payload = _deserialize_bytes_payload(bytes_payload)

    elif message.payload.Is(ObjectProtoPayload.DESCRIPTOR):
        obj = ObjectProtoPayload()
        message.payload.Unpack(obj)
        message_obj.payload = _deserialize_object_payload(obj)

    elif message.payload.Is(BatchProto.DESCRIPTOR):
        batch = BatchProto()
        message.payload.Unpack(batch)
        message_obj.payload = _deserialize_batch_payload(batch)

    return message_obj


def _deserialize_audio_payload(payload: AudioProtoPayload) -> AudioPayload:
    """Deserialize AudioProtoPayload to AudioPayload with numpy array"""
    audio_data = np.frombuffer(payload.audio_data, dtype=payload.dtype)
    audio_data = audio_data.reshape(payload.shape)

    return AudioPayload(
        audio=audio_data,
        sampling_rate=payload.sampling_rate,
        channels=payload.channels,
        audio_format=payload.audio_format,
        start=payload.start,
        end=payload.end,
    )


def _deserialize_image_payload(payload: ImageProtoPayload) -> ImagePayload:
    """Deserialize ImageProtoPayload to ImagePayload with numpy array"""
    image_data = np.frombuffer(payload.image_data, dtype=payload.dtype)

    if payload.depth == 1:
        shape = (payload.height, payload.width)
    else:
        shape = (payload.height, payload.width, payload.depth)

    image_data = image_data.reshape(shape)

    return ImagePayload(
        image=image_data,
        width=payload.width,
        height=payload.height,
        depth=payload.depth,
        pixel_format=payload.pixel_format,
        timestamp=payload.timestamp,
    )


def _deserialize_video_payload(payload: VideoProtoPayload) -> VideoPayload:
    """Deserialize VideoProtoPayload to VideoPayload with numpy arrays list"""
    frames = [_deserialize_image_payload(frame) for frame in payload.frames]

    return VideoPayload(
        video=tuple(frames),
        frames_per_second=payload.frames_per_second,
        codec=payload.codec,
        start=payload.start,
        end=payload.end,
    )


def _deserialize_bytes_payload(payload: BytesProtoPayload) -> BytesPayload:
    """Deserialize BytesProtoPayload to BytesPayload"""
    return BytesPayload(
        cnt=payload.cnt,
    )


def _deserialize_object_payload(payload: ObjectProtoPayload) -> ObjectPayload:
    """Deserialize ObjectProtoPayload to ObjectPayload (dict)"""
    if not payload.HasField('data'):
        return ObjectPayload()

    return ObjectPayload.from_dict(from_typed_value(payload.data))


def _deserialize_batch_payload(payload: BatchProto) -> Batch:
    """Deserialize BatchProto to Batch"""
    return Batch(
        messages=tuple(deserialize_message(m) for m in payload.messages)
    )


# ============================================================================
# TYPED VALUES
# ============================================================================


def to_typed_value(
    value: Any, dropped: list[str] | None = None, path: str = 'value'
) -> TypedValue | None:
    """
    Convert a value to a TypedValue, keeping its type.

    Used for message meta, object payloads and node states. Supported: None,
    bool, int, float, str, bytes, list, tuple, frozenset, dict (with keys of
    any supported type), numpy arrays and scalars, and messages. The
    read-only dicts of a frozen meta come back as plain dicts.

    Parameters
    ----------
    value : Any
        The value to convert.
    dropped : list[str] | None
        None to refuse values of other types. A list to leave them out
        instead: a dict loses the entry, a sequence the item, and the path of
        each value left out is appended to the list.
    path : str
        Name of the value, used in the paths of the values left out.

    Returns
    -------
    TypedValue | None
        The converted value, or None when the value itself was left out.

    Raises
    ------
    TypeError
        If dropped is None and the value, or anything inside it, has another
        type.

    """
    proto = TypedValue()

    def items(values, sequence):
        sequence.SetInParent()

        for index, item in enumerate(values):
            typed = to_typed_value(item, dropped, f'{path}[{index}]')

            if typed is not None:
                sequence.items.append(typed)

    # exact type checks: bool is an int, and subclasses would not come back
    match value:
        case None:
            proto.none = True
        case bool():
            proto.bool_value = value
        case int() if type(value) is int:
            proto.int_value = value
        case float() if type(value) is float:
            proto.float_value = value
        case str() if type(value) is str:
            proto.str_value = value
        case bytes() if type(value) is bytes:
            proto.bytes_value = value
        case list() if type(value) is list:
            items(value, proto.list_value)
        case tuple() if type(value) is tuple:
            items(value, proto.tuple_value)
        case frozenset() if type(value) is frozenset:
            items(value, proto.frozenset_value)
        case dict() if type(value) in (dict, _FrozenDict):
            proto.dict_value.SetInParent()

            for key, item in value.items():
                item_path = f'{path}[{key!r}]'
                typed_key = to_typed_value(key, dropped, item_path)
                typed_item = to_typed_value(item, dropped, item_path)

                if typed_key is None or typed_item is None:
                    continue

                entry = proto.dict_value.entries.add()
                entry.key.CopyFrom(typed_key)
                entry.value.CopyFrom(typed_item)
        case np.ndarray() | np.generic():
            array = np.asarray(value)

            proto.array_value.dtype = array.dtype.str
            proto.array_value.shape.extend(array.shape)
            proto.array_value.data = array.tobytes()
            proto.array_value.scalar = isinstance(value, np.generic)
        case Message():
            proto.message_value.CopyFrom(message_to_proto(value, dropped, path))
        case _ if dropped is not None:
            dropped.append(f'{path} ({type(value).__name__})')

            return None
        case _:
            raise TypeError(
                f'{path}: a {type(value).__name__} cannot be sent to or from '
                'a remote node'
            )

    return proto


def from_typed_value(proto: TypedValue) -> Any:
    """Convert a TypedValue back to the value it was made from"""
    match proto.WhichOneof('kind'):
        case 'none':
            return None
        case 'list_value':
            return [from_typed_value(item) for item in proto.list_value.items]
        case 'tuple_value':
            return tuple(
                from_typed_value(item) for item in proto.tuple_value.items
            )
        case 'frozenset_value':
            return frozenset(
                from_typed_value(item) for item in proto.frozenset_value.items
            )
        case 'dict_value':
            return {
                from_typed_value(entry.key): from_typed_value(entry.value)
                for entry in proto.dict_value.entries
            }
        case 'array_value':
            typed = proto.array_value
            # copied: the protobuf buffer is read-only, the node may write
            array = np.frombuffer(typed.data, dtype=typed.dtype).reshape(
                tuple(typed.shape)
            )

            return array[()] if typed.scalar else array.copy()
        case 'message_value':
            message = deserialize_message(proto.message_value)
            # messages inside a value were frozen, by transmit() or put()
            message._freeze()

            return message
        case None:
            raise ValueError('empty TypedValue')
        case kind:
            return getattr(proto, kind)


# ! FIXME: probably we should change the request_type and response_type
# ! signature: they are meaningful only in the context of requests,
# ! for responses they should be empty, or with a different naming
def create_envelope(
    message: ProtoMessage | None,
    configuration: dict[str, Any],
    metadata: dict[str, Any],
    creator: str,
    pipe_id: str,
    state: dict[str, Any] | None,
    id: str = '',
    priority: int = 1,
    timeout: int = 30,
    response_to: str = None,
    response_type: str = '',
    request_type: str = '',
    stateless: bool = False,
    dropped: list[str] | None = None,
) -> ProtoEnvelope:
    """
    Create envelope around message.

    message is None for a response without output, and state is None when no
    state is sent. dropped works as in to_typed_value, for the state.
    """
    envelope = ProtoEnvelope()
    envelope.id = id or str(uuid.uuid4())
    envelope.sender = creator
    envelope.pipe_id = pipe_id

    if state is not None:
        envelope.state.CopyFrom(to_typed_value(dict(state), dropped, 'state'))

    envelope.created_at = time.time()
    envelope.ttl = int(timeout)
    envelope.request_type = request_type
    envelope.response_type = response_type
    envelope.priority = priority
    envelope.response_to = response_to if response_to is not None else ''
    envelope.configuration.update(configuration)
    envelope.metadata.update(metadata)
    envelope.stateless = stateless

    if message is not None:
        envelope.message.CopyFrom(message)

    return envelope


def deserialize_envelope(envelope: ProtoEnvelope) -> dict[str, Any]:
    """Deserialize ProtoEnvelope to dictionary"""
    message = (
        deserialize_message(envelope.message)
        if envelope.HasField('message')
        else None
    )
    envelope_dict = {
        'id': envelope.id,
        'sender': envelope.sender,
        'pipe_id': envelope.pipe_id,
        'state': (
            from_typed_value(envelope.state)
            if envelope.HasField('state')
            else None
        ),
        'configuration': MessageToDict(envelope.configuration),
        'response_to': envelope.response_to,
        'ttl': envelope.ttl,
        'request_type': envelope.request_type,
        'response_type': envelope.response_type,
        'stateless': envelope.stateless,
        'message': message,
    }
    return envelope_dict
