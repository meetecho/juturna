"""
HttpJson

@ Author: Antonio Bevilacqua
@ Email: abevilacqua@meetecho.com
@ Created at: 2025-10-03

HTTP JSON source node.  Accepts POST /<endpoint> with JSON body. This is a
sourceless node, in the sense that the source function itself only spawns the
server handler and listens forever for incoming requests, while the handler
writes on the node queue whenever a message is received.
"""

from __future__ import annotations

import json
import socket
import threading
import contextlib

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer

from juturna.components import _resource_broker as rb
from juturna.components import Node
from juturna.components import Message
from juturna.payloads import BytesPayload, ObjectPayload


class HttpJson(Node[BytesPayload, ObjectPayload]):
    """HTTP JSON source node."""

    def __init__(
        self,
        host: str,
        port: int | str,
        endpoint: str,
        **kwargs,
    ) -> None:
        """
        Parameters
        ----------
        host : str
            Host address the node will listen on.
        port : int | str
            Listening port. If set to auto, the port will be assigned
            automatically by the resource broker.
        endpoint : str
            Listening endpoint.
        kwargs : dict
            Superclass arguments.

        """
        super().__init__(**kwargs)

        self._host: str = host
        self._port: int | str = port
        self._endpoint: str = endpoint.lstrip('/')
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._sent: int = 0

    def configure(self) -> None:
        """Configure the node before warming up"""
        if self._port == 'auto':
            self._port = rb.get('port')

        self.logger.info(f'configured, listening on port {self._port}')

    def warmup(self) -> None:
        """Warm up the node"""
        handler = self._make_handler()

        self._httpd = HTTPServer(
            (self._host, self._port), handler, bind_and_activate=False
        )

        self._httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._httpd.server_bind()
        self._httpd.server_activate()

        self.logger.info(
            'HTTP JSON source ready on http://%s:%s/%s',
            self._host,
            self._port,
            self._endpoint,
        )

    def start(self) -> None:
        """Start the node"""
        if self._httpd is None:
            raise RuntimeError('warmup() not called')

        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            daemon=True,
            name=f'{self.name}_http',
        )

        self._thread.start()

        super().start()

    def stop(self) -> None:
        """Stop the node"""
        super().stop()

        if self._httpd:
            self._httpd.shutdown()

        if self._thread:
            self._thread.join(timeout=2)

    def destroy(self) -> None:
        """Destroy the node"""
        self.stop()

        if self._httpd:
            self._httpd.server_close()
            self._httpd = None

    def update(self, message: Message[BytesPayload]) -> None:
        """Receive an update message"""
        self.logger.info(f'HTTP server received a message: {message}')

        self.transmit(message)

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        node = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                node.logger.info('POST received')

                if self.path.strip('/') != node._endpoint:
                    self.send_error(HTTPStatus.NOT_FOUND)

                    return

                if self.headers.get('Content-Type') != 'application/json':
                    self.send_error(
                        HTTPStatus.BAD_REQUEST,
                        'Content-Type must be application/json',
                    )

                    return

                content_length = int(self.headers.get('Content-Length', 0))

                if content_length <= 0:
                    self.send_error(HTTPStatus.BAD_REQUEST, 'Empty body')

                    return

                body = self.rfile.read(content_length)

                try:
                    json_content = json.loads(body.decode('utf-8'))
                except ValueError:
                    self.send_error(HTTPStatus.BAD_REQUEST, 'Malformed JSON')

                    return

                msg = Message[ObjectPayload](
                    creator=node.name,
                    version=node._sent,
                    payload=ObjectPayload.from_dict(json_content),
                )

                node.put(msg)
                node._sent += 1

                self.send_response(HTTPStatus.ACCEPTED)
                self.end_headers()

            def do_GET(self) -> None:
                if self.path == '/health':
                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()

                    with contextlib.suppress(
                        BrokenPipeError, ConnectionResetError
                    ):
                        self.wfile.write(b'{"status": "ok"}')
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)

        return _Handler
