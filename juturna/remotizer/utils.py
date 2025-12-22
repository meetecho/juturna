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
from juturna.payloads import (
    AudioPayload,
    ImagePayload,
    VideoPayload,
    BytesPayload,
    ObjectPayload,
)


from generated.payloads_pb2 import (
    ProtoMessage,
    ProtoEnvelope,
    AudioProtoPayload,
    ImageProtoPayload,
    VideoProtoPayload,
    BytesProtoPayload,
    ObjectProtoPayload,
)
from google.protobuf.struct_pb2 import Struct
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
    proto.end = video.end

    return proto


def _bytes_to_proto(bytes_payload: BytesPayload) -> BytesProtoPayload:
    """Convert Python BytesPayload to Protobuf BytesProtoPayload"""
    proto = BytesProtoPayload()
    proto.content = bytes_payload.cnt
    return proto


def _object_to_proto(obj: ObjectPayload) -> ObjectProtoPayload:
    """Convert Python ObjectPayload (dict) to Protobuf ObjectProtoPayload"""
    proto = ObjectProtoPayload()

    # Convert dict to Struct
    struct = Struct()
    struct.update(dict(obj))
    proto.data.CopyFrom(struct)

    return proto


def message_to_proto(message: Message) -> ProtoMessage:
    """
    Convert Python Message to Protobuf ProtoMessage

    Handles all payload types:
    - AudioPayload → AudioProtoPayload
    - ImagePayload → ImageProtoPayload
    - VideoPayload → VideoProtoPayload
    - BytesPayload → BytesProtoPayload
    - ObjectPayload → ObjectProtoPayload

    Parameters
    ----------
    message : Message
        Python Message object with any payload type

    Returns
    -------
    ProtoMessage
        Protobuf message ready for serialization

    """
    proto = ProtoMessage()

    # Copy basic fields
    proto.created_at = message.created_at
    proto.creator = message.creator
    proto.version = message.version

    # Copy metadata
    proto.meta.update(message.meta)
    proto.timers.update(message.timers)

    # Convert payload based on type
    if message.payload is not None:
        if isinstance(message.payload, AudioPayload):
            payload_proto = _audio_to_proto(message.payload)
            proto.payload.Pack(payload_proto)

        elif isinstance(message.payload, ImagePayload):
            payload_proto = _image_to_proto(message.payload)
            proto.payload.Pack(payload_proto)

        elif isinstance(message.payload, VideoPayload):
            payload_proto = _video_to_proto(message.payload)
            proto.payload.Pack(payload_proto)

        elif isinstance(message.payload, BytesPayload):
            payload_proto = _bytes_to_proto(message.payload)
            proto.payload.Pack(payload_proto)

        elif isinstance(message.payload, (ObjectPayload, dict)):
            payload_proto = _object_to_proto(message.payload)
            proto.payload.Pack(payload_proto)

    # TODO: do not rely on this elifs, several aternatives:
    # - 1 use a method defined on the payload classes?
    # like message.payload.to_proto()
    # will this add gprc deps to the core?
    # - 2 use a registry / mapping of payload types to converter functions
    # to make it more extensible, declared outside this function

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
    message_obj.meta.update(dict(message.meta))
    message_obj.timers.update(dict(message.timers))

    # Deserialize payload based on type
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

    # ! actually we do not unpack Batch properly.
    # ! the batch message is a container of messages, so we need to
    # ! unpack each message inside it.
    # ! probably there is an issue with the Batch design:
    # ! it is a Payload _and_ a messages list (with their own payloads).
    # ! probably the Batch should be removed in favor of a Messages array?

    return message_obj  # add finalize here?


def _deserialize_audio_payload(payload: AudioProtoPayload) -> AudioPayload:
    """Deserialize AudioProtoPayload to AudioPayload with numpy array"""
    audio_data = np.frombuffer(payload.audio_data, dtype=payload.dtype)
    audio_data = audio_data.reshape(payload.shape)

    return AudioPayload(
        audio=audio_data,
        sampling_rate=payload.sampling_rate,
        channels=payload.channels,
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
        video=frames,
        frames_per_second=payload.frames_per_second,
        start=payload.start,
        end=payload.end,
    )


def _deserialize_bytes_payload(payload: BytesProtoPayload) -> BytesPayload:
    """Deserialize BytesProtoPayload to BytesPayload"""
    return BytesPayload(
        content=payload.content,
        content_type=payload.content_type,
        filename=payload.filename,
    )


def _deserialize_object_payload(payload: ObjectProtoPayload) -> ObjectPayload:
    """Deserialize ObjectProtoPayload (Struct) to ObjectPayload (dict)"""
    proto_dict = MessageToDict(payload)
    return ObjectPayload.from_dict(proto_dict.get('data', {}))


def create_envelope(
    message: ProtoMessage,
    configuration: dict[str, Any],
    metadata: dict[str, Any],
    creator: str,
    id: str = str(uuid.uuid4()),
    priority: int = 1,
    timeout: int = 30,
    correlation_id: str = str(uuid.uuid4()),
    response_type: str = '',
    request_type: str = '',
) -> ProtoEnvelope:
    """Create envelope around message"""
    assert message is not None

    envelope = ProtoEnvelope()
    envelope.id = id
    envelope.sender = creator
    envelope.receiver = creator
    envelope.correlation_id = correlation_id
    envelope.created_at = time.time()
    envelope.ttl = int(timeout)
    envelope.request_type = request_type
    envelope.response_type = response_type
    envelope.priority = priority
    envelope.configuration.update(configuration)
    envelope.metadata.update(metadata)
    envelope.message.CopyFrom(message)

    return envelope


def deserialize_envelope(envelope: ProtoEnvelope) -> dict[str, Any]:
    """Deserialize ProtoEnvelope to dictionary"""
    message = deserialize_message(envelope.message)
    envelope_dict = {
        'id': envelope.id,
        'sender': envelope.sender,
        'receiver': envelope.receiver,
        'correlation_id': envelope.correlation_id,
        'response_to': envelope.response_to,
        'ttl': envelope.ttl,
        'request_type': envelope.request_type,
        'response_type': envelope.response_type,
        'message': message,
    }
    return envelope_dict
