``JsonWebsocket``
=================

This node opens a websocket server, listening indefinitely for incoming
data. Upon reception, the received bytes will be decoded into a JSON object,
and a message with an ``ObjectPayload`` will be created.

Arguments
---------

``rtx_host : str = "127.0.0.1"``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Host of the websocket server.

``rtx_port : int = 1237``
^^^^^^^^^^^^^^^^^^^^^^^^^

Port of the websocket server.
