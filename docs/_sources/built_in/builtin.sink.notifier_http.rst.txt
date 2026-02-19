``NotifierHTTP``
================

Use this node to send JSON objects or plain text content to a HTTP endpoint.
Depending on the type of content the node is configured to deliver, received
message will be turned into either JSON objects or JSON strings.

Data transmissions are non-blocking: each received message will be assigned a
transmission thread.

Arguments
---------

``endpoint : str = "http://localhost:8080"``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Destination endpoint to send the messages to. It includes the port.

``timeout : int = 20``
^^^^^^^^^^^^^^^^^^^^^^

How long to wait for a transmission response.

``content_type : str = "application/json"``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Transmission data content type. At the moment, the node only supports
``application/json`` and ``text/plain``.
