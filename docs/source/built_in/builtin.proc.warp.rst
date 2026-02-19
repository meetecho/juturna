``Warp`` (auto)
===============

The warping node is the `proxy` node that replaces any local node marked to be
remotised. It is not supposed to be explicitly included in a pipeline, but it
rather gets instantiate automaitcally by juturna when necessary. Its
configuration is built from host, port and timeout values from the remotised
node configuration, and from the remote configuration object that is provided
when the node is instatiated.

Arguments
---------

``grpc_host : str = "localhost"``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The host of the remote juturna service.

``grpc_port : int = 50080``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The port of the remote juturna service.

``timeout : int = 30``
^^^^^^^^^^^^^^^^^^^^^^

Timeout for the gRPC calls, in seconds.

``remote_config : dict``
^^^^^^^^^^^^^^^^^^^^^^^^

Configuration of the remotised node.
