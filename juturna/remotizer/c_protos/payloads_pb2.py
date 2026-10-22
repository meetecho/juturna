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
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0epayloads.proto\x12\x16juturna.proto.payloads\x1a\x19google/protobuf/any.proto\x1a\x1cgoogle/protobuf/struct.proto\"\xa0\x01\n\x11\x41udioProtoPayload\x12\x12\n\naudio_data\x18\x01 \x01(\x0c\x12\r\n\x05\x64type\x18\x02 \x01(\t\x12\r\n\x05shape\x18\x03 \x03(\x05\x12\x15\n\rsampling_rate\x18\x04 \x01(\x05\x12\x10\n\x08\x63hannels\x18\x05 \x01(\x05\x12\r\n\x05start\x18\x06 \x01(\x01\x12\x0b\n\x03\x65nd\x18\x07 \x01(\x01\x12\x14\n\x0c\x61udio_format\x18\x08 \x01(\t\"\x8d\x01\n\x11ImageProtoPayload\x12\x12\n\nimage_data\x18\x01 \x01(\x0c\x12\r\n\x05\x64type\x18\x02 \x01(\t\x12\r\n\x05width\x18\x03 \x01(\x05\x12\x0e\n\x06height\x18\x04 \x01(\x05\x12\r\n\x05\x64\x65pth\x18\x05 \x01(\x05\x12\x14\n\x0cpixel_format\x18\x06 \x01(\t\x12\x11\n\ttimestamp\x18\x07 \x01(\x01\"\x94\x01\n\x11VideoProtoPayload\x12\x39\n\x06\x66rames\x18\x01 \x03(\x0b\x32).juturna.proto.payloads.ImageProtoPayload\x12\x19\n\x11\x66rames_per_second\x18\x02 \x01(\x01\x12\r\n\x05start\x18\x03 \x01(\x01\x12\x0b\n\x03\x65nd\x18\x04 \x01(\x01\x12\r\n\x05\x63odec\x18\x05 \x01(\t\".\n\x11\x42ytesProtoPayload\x12\x0b\n\x03\x63nt\x18\x01 \x01(\x0c\x12\x0c\n\x04size\x18\x02 \x01(\x03\"D\n\nBatchProto\x12\x36\n\x08messages\x18\x01 \x03(\x0b\x32$.juturna.proto.payloads.ProtoMessage\";\n\x12ObjectProtoPayload\x12%\n\x04\x64\x61ta\x18\x01 \x01(\x0b\x32\x17.google.protobuf.Struct\"\x8f\x02\n\x0cProtoMessage\x12\x12\n\ncreated_at\x18\x01 \x01(\x01\x12\x0f\n\x07\x63reator\x18\x02 \x01(\t\x12\x0f\n\x07version\x18\x03 \x01(\x05\x12%\n\x07payload\x18\x04 \x01(\x0b\x32\x14.google.protobuf.Any\x12%\n\x04meta\x18\x05 \x01(\x0b\x32\x17.google.protobuf.Struct\x12@\n\x06timers\x18\x06 \x03(\x0b\x32\x30.juturna.proto.payloads.ProtoMessage.TimersEntry\x12\n\n\x02id\x18\n \x01(\x05\x1a-\n\x0bTimersEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\x01:\x02\x38\x01\"\xc3\x03\n\nTypedValue\x12\x0e\n\x04none\x18\x01 \x01(\x08H\x00\x12\x14\n\nbool_value\x18\x02 \x01(\x08H\x00\x12\x13\n\tint_value\x18\x03 \x01(\x12H\x00\x12\x15\n\x0b\x66loat_value\x18\x04 \x01(\x01H\x00\x12\x13\n\tstr_value\x18\x05 \x01(\tH\x00\x12\x15\n\x0b\x62ytes_value\x18\x06 \x01(\x0cH\x00\x12;\n\nlist_value\x18\x07 \x01(\x0b\x32%.juturna.proto.payloads.TypedSequenceH\x00\x12<\n\x0btuple_value\x18\x08 \x01(\x0b\x32%.juturna.proto.payloads.TypedSequenceH\x00\x12:\n\ndict_value\x18\t \x01(\x0b\x32$.juturna.proto.payloads.TypedMappingH\x00\x12\x39\n\x0b\x61rray_value\x18\n \x01(\x0b\x32\".juturna.proto.payloads.TypedArrayH\x00\x12=\n\rmessage_value\x18\x0b \x01(\x0b\x32$.juturna.proto.payloads.ProtoMessageH\x00\x42\x06\n\x04kind\"B\n\rTypedSequence\x12\x31\n\x05items\x18\x01 \x03(\x0b\x32\".juturna.proto.payloads.TypedValue\"\xb8\x01\n\x0cTypedMapping\x12;\n\x07\x65ntries\x18\x01 \x03(\x0b\x32*.juturna.proto.payloads.TypedMapping.Entry\x1ak\n\x05\x45ntry\x12/\n\x03key\x18\x01 \x01(\x0b\x32\".juturna.proto.payloads.TypedValue\x12\x31\n\x05value\x18\x02 \x01(\x0b\x32\".juturna.proto.payloads.TypedValue\"H\n\nTypedArray\x12\r\n\x05\x64type\x18\x01 \x01(\t\x12\r\n\x05shape\x18\x02 \x03(\x03\x12\x0c\n\x04\x64\x61ta\x18\x03 \x01(\x0c\x12\x0e\n\x06scalar\x18\x04 \x01(\x08\"\xc9\x03\n\rProtoEnvelope\x12\n\n\x02id\x18\x01 \x01(\t\x12\x35\n\x07message\x18\x02 \x01(\x0b\x32$.juturna.proto.payloads.ProtoMessage\x12\x0e\n\x06sender\x18\x03 \x01(\t\x12\x10\n\x08receiver\x18\x04 \x01(\t\x12\x0f\n\x07pipe_id\x18\x05 \x01(\t\x12&\n\x05state\x18\x06 \x01(\x0b\x32\x17.google.protobuf.Struct\x12\x13\n\x0bresponse_to\x18\x07 \x01(\t\x12\x0b\n\x03ttl\x18\x08 \x01(\x03\x12\x12\n\ncreated_at\x18\t \x01(\x01\x12.\n\rconfiguration\x18\n \x01(\x0b\x32\x17.google.protobuf.Struct\x12)\n\x08metadata\x18\x0b \x01(\x0b\x32\x17.google.protobuf.Struct\x12\x10\n\x08priority\x18\x0c \x01(\x05\x12\x14\n\x0crequest_type\x18\r \x01(\t\x12\x15\n\rresponse_type\x18\x0e \x01(\t\x12\x11\n\tstateless\x18\x0f \x01(\x08\x12\x37\n\x0btyped_state\x18\x10 \x01(\x0b\x32\".juturna.proto.payloads.TypedValue\"\x8d\x01\n\x16\x43ompressedProtoPayload\x12\x13\n\x0b\x63ompression\x18\x01 \x01(\t\x12\x17\n\x0f\x63ompressed_data\x18\x02 \x01(\x0c\x12\x15\n\roriginal_size\x18\x03 \x01(\x03\x12\x17\n\x0f\x63ompressed_size\x18\x04 \x01(\x03\x12\x15\n\roriginal_type\x18\x05 \x01(\tb\x06proto3')
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
    _globals['_OBJECTPROTOPAYLOAD']._serialized_end = 734
    _globals['_PROTOMESSAGE']._serialized_start = 737
    _globals['_PROTOMESSAGE']._serialized_end = 1008
    _globals['_PROTOMESSAGE_TIMERSENTRY']._serialized_start = 963
    _globals['_PROTOMESSAGE_TIMERSENTRY']._serialized_end = 1008
    _globals['_TYPEDVALUE']._serialized_start = 1011
    _globals['_TYPEDVALUE']._serialized_end = 1462
    _globals['_TYPEDSEQUENCE']._serialized_start = 1464
    _globals['_TYPEDSEQUENCE']._serialized_end = 1530
    _globals['_TYPEDMAPPING']._serialized_start = 1533
    _globals['_TYPEDMAPPING']._serialized_end = 1717
    _globals['_TYPEDMAPPING_ENTRY']._serialized_start = 1610
    _globals['_TYPEDMAPPING_ENTRY']._serialized_end = 1717
    _globals['_TYPEDARRAY']._serialized_start = 1719
    _globals['_TYPEDARRAY']._serialized_end = 1791
    _globals['_PROTOENVELOPE']._serialized_start = 1794
    _globals['_PROTOENVELOPE']._serialized_end = 2251
    _globals['_COMPRESSEDPROTOPAYLOAD']._serialized_start = 2254
    _globals['_COMPRESSEDPROTOPAYLOAD']._serialized_end = 2395
