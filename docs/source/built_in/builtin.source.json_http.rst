``HttpJson``
============

This source node spawns a HTTP server, listening for ``POST`` requests on a
configured ``/<endpoint>``. Generated messages are produced with the JSON
objects in the received requests.

Additionally, the node offers a ``GET``table ``/health`` API that can be queried
to check if the node is running properly.

Arguments
---------

``endpoint : str = "juturna"``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The endpoint of the listening server.

``port : int = 8888``
^^^^^^^^^^^^^^^^^^^^^

The port of the listening server.
