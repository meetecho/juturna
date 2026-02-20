``NotifierWebsocket``
=====================

Use this node to transmit messages to a remote websocket endpoint. The node is
capable of transmitting any type of message, however, messages will first be
converted into JSON strings, then transmitted.

Each new message received by the node will generate a new connection with the
remote endpoint.

Arguments
---------

``endpoint : str = "127.0.0.1:1237"``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Destination endpoint. It includes the port.
