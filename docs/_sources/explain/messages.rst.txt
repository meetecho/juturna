Messages and payloads
=====================

The ``Message`` class is Juturna's fundamental unit of data transfer. Messages
are designed to carry data payloads decorated with versioning, timing, and
arbitrary metadata. Every byte that flows through a pipeline flows inside a
message.

Considering how messages are designed, they can be seen as a two-part entity: a
message acts as an immutable envelope, carrying data and its corresponding
metadata, while a payload contains the actual domain data to be transferred.

This design favours:

- **type safety**, as ideally nodes always have both knowledge of the type of
  data they will receive as input, and instruction for how to generate data to
  transmit as output;
- **separation of concerns**, since payload processing is decoupled from
  metadata tracking;
- **observability**, as every message carries its own timing and provenance
  data;
- **isolation** as a direct consequence of the nature of messages (at any given
  time, a message can be evaulated without extra information needed on its
  context).

.. image:: ../_static/img/message.svg
   :alt: message
   :width: 60%
   :align: center

Messages
--------

As said, a message is just a simple data container. It carries a payload, plus
some extra fields that can be useful to determine who generated it, when, and in
which order comared to other messages.

Other than its basic properties, such as `creator`, `version`, `payload`, `meta`
and `timers`, a message offers a few methods that can help with managing its
content and representation:

``message.to_dict()`` and ``message.to_json(encoder)`` offer serialisation
options for when a message needs to be converted, stored, or transmitted to a
destination that requires serialised content (these are also used by nodes
through their ``dump_json()`` method).

``message.timeit(t_name)`` is a context manager supposed to ease the collection
of elapsed time during processing. It can be used to isolate a specific
operation or group of operations, and store their execution time:

.. code-block:: python

  with message.timeit('inference_time'):
      annotated_image = model.infer(message.payload.image)

  message.timers
  # {'inference_time': <EXEC_TIME>}

Payloads
--------

All payload types inherit from a ``BasePayload``, which provides a ``clone()``
method for deep copying. This can be useful when the same message must be sent
to multiple destinations without shared state.

Juturna offers a number of built-in media and structural payloads.

- ``AudioPayload`` carries ``np.ndarray`` audio waveforms with metadata
  (sampling rate, channels, start/end timestamps).
- ``ImagePayload`` wraps multidimensional ``np.ndarray`` arrays containing
  images, attaching metadata such as width, height, dept, pixel format, and
  timestamp.
- ``VideoPayload`` holds to a list of ``ImagePayload``, with metadata on frames
  per second and duration (start and end timestamps).
- ``BytesPayload`` only contains an array of bytes.
- ``Batch`` contains a list of messages. A batch is usually produced by a node
  buffer whenever its synchroniser marked multiple messages for processing.
- ``ObjectPayload`` is a subclass of ``dict`` design to hold arbitrary key-value
  pairs.