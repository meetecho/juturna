"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 6, 31, 1, '', 'messaging_service.proto')
_sym_db = _symbol_database.Default()
from . import payloads_pb2 as payloads__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x17messaging_service.proto\x12\x17juturna.proto.messaging\x1a\x0epayloads.proto2r\n\x10MessagingService\x12^\n\x0eSendAndReceive\x12%.juturna.proto.payloads.ProtoEnvelope\x1a%.juturna.proto.payloads.ProtoEnvelopeb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'messaging_service_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_MESSAGINGSERVICE']._serialized_start = 68
    _globals['_MESSAGINGSERVICE']._serialized_end = 182
