"""Client and server classes corresponding to protobuf-defined services."""

import grpc
from . import payloads_pb2 as payloads__pb2

GRPC_GENERATED_VERSION = '1.76.0'
GRPC_VERSION = grpc.__version__
_version_not_supported = False
try:
    from grpc._utilities import first_version_is_lower

    _version_not_supported = first_version_is_lower(
        GRPC_VERSION, GRPC_GENERATED_VERSION
    )
except ImportError:
    _version_not_supported = True
if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + ' but the generated code in messaging_service_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class MessagingServiceStub:
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """
        Constructor.

        Args:
            channel: A grpc.Channel.

        """
        self.SendAndReceive = channel.unary_unary(
            '/juturna.proto.messaging.MessagingService/SendAndReceive',
            request_serializer=payloads__pb2.ProtoEnvelope.SerializeToString,
            response_deserializer=payloads__pb2.ProtoEnvelope.FromString,
            _registered_method=True,
        )


class MessagingServiceServicer:
    """Missing associated documentation comment in .proto file."""

    def SendAndReceive(self, request, context):
        """
        Send a message and get acknowledgment
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_MessagingServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
        'SendAndReceive': grpc.unary_unary_rpc_method_handler(
            servicer.SendAndReceive,
            request_deserializer=payloads__pb2.ProtoEnvelope.FromString,
            response_serializer=payloads__pb2.ProtoEnvelope.SerializeToString,
        )
    }
    generic_handler = grpc.method_handlers_generic_handler(
        'juturna.proto.messaging.MessagingService', rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers(
        'juturna.proto.messaging.MessagingService', rpc_method_handlers
    )


class MessagingService:
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def SendAndReceive(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/juturna.proto.messaging.MessagingService/SendAndReceive',
            payloads__pb2.ProtoEnvelope.SerializeToString,
            payloads__pb2.ProtoEnvelope.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True,
        )
