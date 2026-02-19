``NotifierUDP``
===============

Use this node to transmit byte data to a remote UDP socket, managing
segmentation so that the receiving end can reassemble the data even if they did
not arrive in the right order.

The node will convert messages into JSON strings, then chunk it so that no
single UDP packet exceeds a configured payload size (including the header).
Each chunk object looks like this:

.. code-block:: python

    chunk = {
        'seq': message.version,
        'frag': i % max_chunks,
        'tot': total_chunks,
        'data': payload_chunk,
    }

So, a juturna message is identified by the ``seq`` field, while the fragment
number by the ``frag`` field.

Arguments
---------

``endpoint : str = "127.0.0.1"``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Address of the destination socket.

``port : int = 12345``
^^^^^^^^^^^^^^^^^^^^^^

Port of the destination socket.

``payload_size : int = 1024``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Size of each payload, including the header.

``max_sequence : int = 9999``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Maximum sequence number for juturna message before resetting.

``max_chunks : int = 1000``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Maximum chunk number for fragments before resetting.

``encoding : str = "utf8"``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Encoding to use on the data.

``encode_b64 : bool = true``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If true, data will be encoded in Base64.
