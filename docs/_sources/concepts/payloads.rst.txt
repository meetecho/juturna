########
Payloads
########

A payload is a data container used to store and transfer different types of
multimedia and data within messages.

BasePayload
===========

+------------------+-------------+----------------------------------+
| property         | type        | description                      |
+==================+=============+==================================+
| ``self.clone()`` | ``method``  | creates a deep copy of the       |
|                  |             | payload instance                 |
+------------------+-------------+----------------------------------+

AudioPayload
============

+------------------------+----------------+----------------------------------+
| property               | type           | description                      |
+========================+================+==================================+
| ``self.audio``         | ``np.ndarray`` | NumPy array containing the       |
|                        |                | audio data                       |
+------------------------+----------------+----------------------------------+
| ``self.sampling_rate`` | ``int``        | audio sampling rate in Hz        |
+------------------------+----------------+----------------------------------+
| ``self.channels``      | ``int``        | number of audio channels         |
+------------------------+----------------+----------------------------------+
| ``self.start``         | ``float``      | start time in seconds            |
+------------------------+----------------+----------------------------------+
| ``self.end``           | ``float``      | end time in seconds              |
+------------------------+----------------+----------------------------------+

An empty AudioPayload is created with:

- ``audio`` set to ``np.ndarray(0)``
- ``sampling_rate`` set to ``-1``
- ``channels`` set to ``-1``
- ``start`` set to ``-1.0``
- ``end`` set to ``-1.0``

ImagePayload
============

+-----------------------+----------------+----------------------------------+
| property              | type           | description                      |
+=======================+================+==================================+
| ``self.image``        | ``np.ndarray`` | NumPy array containing the       |
|                       |                | image data                       |
+-----------------------+----------------+----------------------------------+
| ``self.width``        | ``int``        | image width in pixels            |
+-----------------------+----------------+----------------------------------+
| ``self.height``       | ``int``        | image height in pixels           |
+-----------------------+----------------+----------------------------------+
| ``self.depth``        | ``int``        | image depth/channels (e.g., 3    |
|                       |                | for RGB, 4 for RGBA)             |
+-----------------------+----------------+----------------------------------+
| ``self.pixel_format`` | ``str``        | pixel format description (e.g.,  |
|                       |                | 'RGB', 'RGBA', 'BGR')            |
+-----------------------+----------------+----------------------------------+
| ``self.timestamp``    | ``float``      | timestamp associated with the    |
|                       |                | image                            |
+-----------------------+----------------+----------------------------------+

An empty ImagePayload is created with:

- ``image`` set to ``np.ndarray([0, 0])``
- ``width`` set to ``-1``
- ``height`` set to ``-1``
- ``depth`` set to ``-1``
- ``pixel_format`` set to ``''``
- ``timestamp`` set to ``-1.0``

VideoPayload
============

+----------------------------+-------------------------+-------------------------------+
| property                   | type                    | description                   |
+============================+=========================+===============================+
| ``self.video``             | ``List[ImagePayload]``  | list of ImagePayload objects  |
|                            |                         | representing video frames     |
+----------------------------+-------------------------+-------------------------------+
| ``self.frames_per_second`` | ``float``               | video frame rate in frames    |
|                            |                         | per second                    |
+----------------------------+-------------------------+-------------------------------+
| ``self.start``             | ``float``               | start time in seconds         |
+----------------------------+-------------------------+-------------------------------+
| ``self.end``               | ``float``               | end time in seconds           |
+----------------------------+-------------------------+-------------------------------+

An empty VideoPayload is created with:

- ``video`` set to ``list()``
- ``frames_per_second`` set to ``-1.0``
- ``start`` set to ``-1.0``
- ``end`` set to ``-1.0``

BytesPayload
============

+----------------+----------+----------------------------------+
| property       | type     | description                      |
+================+==========+==================================+
| ``self.cnt``   | ``bytes`` | binary data content             |
+----------------+----------+----------------------------------+

An empty BytesPayload is created with:

- ``cnt`` set to ``bytes()``

ObjectPayload
=============

+-------------------+----------+--------------------------------+
| property          | type     | description                    |
+===================+==========+================================+
| (inherits from    | ``dict`` | dictionary-like access for     |
| dict)             |          | arbitrary object data          |
+-------------------+----------+--------------------------------+

An empty ObjectPayload is created as an empty dictionary.

Notes:

- all payload classes inherit from ``BasePayload`` and provide a ``clone()`` method
  for deep copying
- default values of ``-1`` for numeric fields and empty strings/collections
  typically indicate unspecified or uninitialized values
- ``ObjectPayload`` combines dictionary functionality with payload cloning
  capabilities