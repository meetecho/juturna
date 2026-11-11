"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 6, 31, 1, '', 'payloads.proto')
_sym_db = _symbol_database.Default()
from google.protobuf import any_pb2 as google_dot_protobuf_dot_any__pb2
from google.protobuf import struct_pb2 as google_dot_protobuf_dot_struct__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0epayloads.proto\x12\x16juturna.proto.payloads\x1a\x19google/protobuf/any.proto\x1a\x1cgoogle/protobuf/struct.proto"\xa0\x01\n\x11AudioProtoPayload\x12\x12\n\naudio_data\x18\x01 \x01(\x0c\x12\r\n\x05dtype\x18\x02 \x01(\t\x12\r\n\x05shape\x18\x03 \x03(\x05\x12\x15\n\rsampling_rate\x18\x04 \x01(\x05\x12\x10\n\x08channels\x18\x05 \x01(\x05\x12\r\n\x05start\x18\x06 \x01(\x01\x12\x0b\n\x03end\x18\x07 \x01(\x01\x12\x14\n\x0caudio_format\x18\x08 \x01(\t"\x8d\x01\n\x11ImageProtoPayload\x12\x12\n\nimage_data\x18\x01 \x01(\x0c\x12\r\n\x05dtype\x18\x02 \x01(\t\x12\r\n\x05width\x18\x03 \x01(\x05\x12\x0e\n\x06height\x18\x04 \x01(\x05\x12\r\n\x05depth\x18\x05 \x01(\x05\x12\x14\n\x0cpixel_format\x18\x06 \x01(\t\x12\x11\n\ttimestamp\x18\x07 \x01(\x01"\x94\x01\n\x11VideoProtoPayload\x129\n\x06frames\x18\x01 \x03(\x0b2).juturna.proto.payloads.ImageProtoPayload\x12\x19\n\x11frames_per_second\x18\x02 \x01(\x01\x12\r\n\x05start\x18\x03 \x01(\x01\x12\x0b\n\x03end\x18\x04 \x01(\x01\x12\r\n\x05codec\x18\x05 \x01(\t".\n\x11BytesProtoPayload\x12\x0b\n\x03cnt\x18\x01 \x01(\x0c\x12\x0c\n\x04size\x18\x02 \x01(\x03"D\n\nBatchProto\x126\n\x08messages\x18\x01 \x03(\x0b2$.juturna.proto.payloads.ProtoMessage"F\n\x12ObjectProtoPayload\x120\n\x04data\x18\x01 \x01(\x0b2".juturna.proto.payloads.TypedValue"\x9a\x02\n\x0cProtoMessage\x12\x12\n\ncreated_at\x18\x01 \x01(\x01\x12\x0f\n\x07creator\x18\x02 \x01(\t\x12\x0f\n\x07version\x18\x03 \x01(\x03\x12%\n\x07payload\x18\x04 \x01(\x0b2\x14.google.protobuf.Any\x120\n\x04meta\x18\x05 \x01(\x0b2".juturna.proto.payloads.TypedValue\x12@\n\x06timers\x18\x06 \x03(\x0b20.juturna.proto.payloads.ProtoMessage.TimersEntry\x12\n\n\x02id\x18\n \x01(\x03\x1a-\n\x0bTimersEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\x01:\x028\x01"\x85\x04\n\nTypedValue\x12\x0e\n\x04none\x18\x01 \x01(\x08H\x00\x12\x14\n\nbool_value\x18\x02 \x01(\x08H\x00\x12\x13\n\tint_value\x18\x03 \x01(\x12H\x00\x12\x15\n\x0bfloat_value\x18\x04 \x01(\x01H\x00\x12\x13\n\tstr_value\x18\x05 \x01(\tH\x00\x12\x15\n\x0bbytes_value\x18\x06 \x01(\x0cH\x00\x12;\n\nlist_value\x18\x07 \x01(\x0b2%.juturna.proto.payloads.TypedSequenceH\x00\x12<\n\x0btuple_value\x18\x08 \x01(\x0b2%.juturna.proto.payloads.TypedSequenceH\x00\x12:\n\ndict_value\x18\t \x01(\x0b2$.juturna.proto.payloads.TypedMappingH\x00\x129\n\x0barray_value\x18\n \x01(\x0b2".juturna.proto.payloads.TypedArrayH\x00\x12=\n\rmessage_value\x18\x0b \x01(\x0b2$.juturna.proto.payloads.ProtoMessageH\x00\x12@\n\x0ffrozenset_value\x18\x0c \x01(\x0b2%.juturna.proto.payloads.TypedSequenceH\x00B\x06\n\x04kind"B\n\rTypedSequence\x121\n\x05items\x18\x01 \x03(\x0b2".juturna.proto.payloads.TypedValue"\xb8\x01\n\x0cTypedMapping\x12;\n\x07entries\x18\x01 \x03(\x0b2*.juturna.proto.payloads.TypedMapping.Entry\x1ak\n\x05Entry\x12/\n\x03key\x18\x01 \x01(\x0b2".juturna.proto.payloads.TypedValue\x121\n\x05value\x18\x02 \x01(\x0b2".juturna.proto.payloads.TypedValue"H\n\nTypedArray\x12\r\n\x05dtype\x18\x01 \x01(\t\x12\r\n\x05shape\x18\x02 \x03(\x03\x12\x0c\n\x04data\x18\x03 \x01(\x0c\x12\x0e\n\x06scalar\x18\x04 \x01(\x08"\xc4\x03\n\rProtoEnvelope\x12\n\n\x02id\x18\x01 \x01(\t\x125\n\x07message\x18\x02 \x01(\x0b2$.juturna.proto.payloads.ProtoMessage\x12\x0e\n\x06sender\x18\x03 \x01(\t\x12\x0f\n\x07pipe_id\x18\x05 \x01(\t\x12\x13\n\x0bresponse_to\x18\x07 \x01(\t\x12\x0b\n\x03ttl\x18\x08 \x01(\x03\x12\x12\n\ncreated_at\x18\t \x01(\x01\x12.\n\rconfiguration\x18\n \x01(\x0b2\x17.google.protobuf.Struct\x12)\n\x08metadata\x18\x0b \x01(\x0b2\x17.google.protobuf.Struct\x12\x11\n\tstateless\x18\x0f \x01(\x08\x121\n\x05state\x18\x10 \x01(\x0b2".juturna.proto.payloads.TypedValue\x12\x18\n\x10protocol_version\x18\x11 \x01(\r\x12\x0f\n\x07session\x18\x12 \x01(\tJ\x04\x08\x04\x10\x05J\x04\x08\x06\x10\x07J\x04\x08\x0c\x10\rJ\x04\x08\r\x10\x0eJ\x04\x08\x0e\x10\x0fR\x08receiverR\x08priorityR\x0crequest_typeR\rresponse_typeb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'payloads_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_PROTOMESSAGE_TIMERSENTRY']._loaded_options = None
    _globals['_PROTOMESSAGE_TIMERSENTRY']._serialized_options = b'8\x01'
    _globals['_AUDIOPROTOPAYLOAD']._serialized_start = 100
    _globals['_AUDIOPROTOPAYLOAD']._serialized_end = 260
    _globals['_IMAGEPROTOPAYLOAD']._serialized_start = 263
    _globals['_IMAGEPROTOPAYLOAD']._serialized_end = 404
    _globals['_VIDEOPROTOPAYLOAD']._serialized_start = 407
    _globals['_VIDEOPROTOPAYLOAD']._serialized_end = 555
    _globals['_BYTESPROTOPAYLOAD']._serialized_start = 557
    _globals['_BYTESPROTOPAYLOAD']._serialized_end = 603
    _globals['_BATCHPROTO']._serialized_start = 605
    _globals['_BATCHPROTO']._serialized_end = 673
    _globals['_OBJECTPROTOPAYLOAD']._serialized_start = 675
    _globals['_OBJECTPROTOPAYLOAD']._serialized_end = 745
    _globals['_PROTOMESSAGE']._serialized_start = 748
    _globals['_PROTOMESSAGE']._serialized_end = 1030
    _globals['_PROTOMESSAGE_TIMERSENTRY']._serialized_start = 985
    _globals['_PROTOMESSAGE_TIMERSENTRY']._serialized_end = 1030
    _globals['_TYPEDVALUE']._serialized_start = 1033
    _globals['_TYPEDVALUE']._serialized_end = 1550
    _globals['_TYPEDSEQUENCE']._serialized_start = 1552
    _globals['_TYPEDSEQUENCE']._serialized_end = 1618
    _globals['_TYPEDMAPPING']._serialized_start = 1621
    _globals['_TYPEDMAPPING']._serialized_end = 1805
    _globals['_TYPEDMAPPING_ENTRY']._serialized_start = 1698
    _globals['_TYPEDMAPPING_ENTRY']._serialized_end = 1805
    _globals['_TYPEDARRAY']._serialized_start = 1807
    _globals['_TYPEDARRAY']._serialized_end = 1879
    _globals['_PROTOENVELOPE']._serialized_start = 1882
    _globals['_PROTOENVELOPE']._serialized_end = 2334
