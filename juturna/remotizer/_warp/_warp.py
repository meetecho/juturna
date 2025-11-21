"""
Warp Node

@ Author: Paolo Saviano
@ Email: psaviano@meetecho.com

Generic gRPC remote node using Juturna's protobuf messaging.
"""

import grpc

from generated import messaging_service_pb2_grpc

from juturna.remotizer.utils import (
    message_to_proto,
    create_envelope,
    deserialize_message,
)

from juturna.components import Message
from juturna.components import Node


from typing import TypeVar

T_Input = TypeVar('T_Input')
T_Output = TypeVar('T_Output')


class Warp[T_Input, T_Output](Node(T_Input, T_Output)):
    """
    Type Parameters
    ---------------
    T_Input : TypeVar
        Input payload type (e.g., AudioPayload, ImagePayload)
    T_Output : TypeVar
        Output payload type (e.g., AudioPayload, ImagePayload)
    """

    def __init__(
        self,
        grpc_host: str,
        grpc_port: int,
        timeout: int,
        remote_config: dict,
        **kwargs,
    ):
        """
        Parameters
        ----------
        grpc_host : str
            gRPC server hostname.
        grpc_port : int
            gRPC server port.
        timeout : int
            Timeout for gRPC calls in seconds.
        remote_config : dict
            Missing description.
        kwargs : dict
            Supernode arguments.

        """
        super().__init__(**kwargs)

        self._grpc_host = grpc_host
        self._grpc_port = grpc_port
        self._timeout = timeout
        self._remote_config = remote_config

        self.logger.info('warp node initialized')

    def warmup(self):
        """Warmup the node"""
        # Setup gRPC channel and stub
        self.channel = grpc.insecure_channel(
            f' {self._grpc_host}:{self._grpc_port}',
            options=[
                ('grpc.max_send_message_length', 100 * 1024 * 1024),  # 100MB
                ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
            ],
        )

        # Create stub: it stubs the remote service for the client-proxy;
        # it will be defined as MessagingServiceImpl on the server side
        self.stub = messaging_service_pb2_grpc.MessagingServiceStub(
            self.channel
        )

        self.logger.info(f'warmup node: {self.name}')

    def update(self, message: Message[T_Input]):
        """
        Send message via gRPC and wait for response

        The message can contain any payload type (T_Input).
        Response will contain payload of type T_Output.

        Parameters
        ----------
        message : Message[T_Input]
            The message to send with input payload type

        """
        try:
            # 1. Convert Python Message to Protobuf ProtoMessage
            self.logger.debug('converting message to protobuf...')
            message_proto = message_to_proto(message)

            # 2. Create ProtoEnvelope
            self.logger.debug('creating envelope...')
            envelope = create_envelope(
                message=message_proto,
                creator=self.name,
                request_type=type(message.payload).__name__,
                response_type=type(self).T_Output.__name__,
                priority=0,
                timeout=self._timeout,
                configuration={},
                metadata={},
            )

            envelope.configuration.update(self._remote_config)

            awaited_correlation_id = envelope.correlation_id
            self.logger.debug(
                f'envelope created with correlation_id={awaited_correlation_id}'
            )
            # 3. Send via gRPC and wait for response
            self.logger.info(f'sending message (envelope_id={envelope.id})...')

            response_envelope = self.stub.SendAndReceive(
                envelope, timeout=self._timeout
            )

            self.logger.info(
                f'received response (envelope_id={response_envelope.id})'
            )
            self.logger.debug(
                f'response correlation_id={response_envelope.correlation_id}'
            )

            # 4. check correlation
            assert awaited_correlation_id == response_envelope.correlation_id, (
                'correlation_id mismatch: '
                f'expected {awaited_correlation_id}, '
                f'got {response_envelope.correlation_id}'
            )

            # 4. Convert response from Protobuf back to Message
            self.logger.debug('converting response to Message...')
            to_send: Message[T_Output] = deserialize_message(
                response_envelope.message
            )

            # 5. Call transmit with the response
            self.transmit(to_send)
            self.logger.info(f'transmit: {to_send.version}')

        except grpc.RpcError as e:
            self.logger.error(f'gRPC error: {e.code()} - {e.details()}')
            raise
        except Exception as e:
            self.logger.error(f'Error in update: {e}', exc_info=True)
            raise
