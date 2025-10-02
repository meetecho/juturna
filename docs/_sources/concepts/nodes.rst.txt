##############
Built-in nodes
##############

Source
======

``audio_rtp``
-------------
This node consumes a remote RTP audio stream, and makes it available to its
destinations as chunks of a configurable length.

Internally, ``audio_rtp`` spawns a local ``ffmpeg`` thread that will receive
the stream on a port picked at runtime and make it available to the standard
output. Received samples will be collected and transmitted

This approach allows to demand all the decode-encode heavy lifting to
``ffmpeg``.

+------------------+---------------+----------------------------------------+
| argument         | type          | description                            |
+==================+===============+========================================+
| ``rec_host``     | ``str``       | the host from which the stream will be |
|                  |               | received                               |
+------------------+---------------+----------------------------------------+
| ``rec_port``     | ``int | str`` | the port the stream will be received on|
+------------------+---------------+----------------------------------------+
| ``audio_rate``   | ``int``       | rate of the receiving audio            |
+------------------+---------------+----------------------------------------+
|  ``block_size``  | ``int``       | length (in seconds) of the audio chunks|
|                  |               | to generate                            |
+------------------+---------------+----------------------------------------+
|  ``channels``    | ``int``       | number of channels of the receiving    |
|                  |               | audio                                  |
+------------------+---------------+----------------------------------------+
| ``payload_type`` | ``dict``      | payload type as specified in the       |
|                  |               | incoming stream                        |
+------------------+---------------+----------------------------------------+

During the warmup phase, this node will write in its node folder the sdp file
with all the relevant information about the local stream.

Nodes:

- the node automatically selects a receiving port if ``rec_port`` is set to
  ``auto`` in the configuration, otherwise will use the provided port; the same
  applies to the local transmitting port
- this node accumulates audio samples until the temporal length of all the
  samples reach ``block_size``, computed in seconds; this length is computed
  using ``audio_rate``, so make sure it matches the sources'

``audio_file``
--------------
This node loads an audio file, and makes it available to any destinations node
in chunks of a coinfigurable length.

+------------------+----------+----------------------------------------+
| argument         | type     | description                            |
+==================+==========+========================================+
| ``file_source``  | ``str``  | path of the source audio file          |
+------------------+----------+----------------------------------------+
| ``audio_rate``   | ``int``  | rate of the audio file                 |
+------------------+----------+----------------------------------------+
|  ``block_size``  | ``int``  | length (in seconds) of the audio chunks|
|                  |          | to generate                            |
+------------------+----------+----------------------------------------+

``video_rtp``
-------------
This node consumes a remote RTP video stream, and makes it available to its
destinations as either individual frames or collections of frames, depending on
its working mode. Internally, it works in a similar fashion to the `audio_rtp`
node.

+--------------------+---------------+----------------------------------------+
| argument           | type          | description                            |
+====================+===============+========================================+
| ``rec_host``       | ``str``       | the host from which the stream will be |
|                    |               | received                               |
+--------------------+---------------+----------------------------------------+
| ``rec_port``       | ``int | str`` | the port on which the stream will be   |
|                    |               | received                               |
+--------------------+---------------+----------------------------------------+
| ``width``          | ``int``       | width of the received video stream     |
+--------------------+---------------+----------------------------------------+
| ``height``         | ``int``       | height of the received video stream    |
+--------------------+---------------+----------------------------------------+
| ``codec``          | ``int``       | the codec of the source stream         |
+--------------------+---------------+----------------------------------------+
| ``payload_type``   | ``dict``      | payload type as specified in the       |
|                    |               | incoming stream                        |
+--------------------+---------------+----------------------------------------+

Notes:

- the node automatically selects a receiving port if ``rec_port`` is set to
  ``auto`` in the configuration, otherwise will use the provided port

Sink
====

``notifier_http``
-----------------
A simple notifier that transmits data to a HTTP endpoint.

+------------------+----------+---------------------------------+
| argument         | type     | description                     |
+==================+==========+=================================+
| ``endpoint``     | ``str``  | destination endpoint            |
+------------------+----------+---------------------------------+
| ``timeout``      | ``int``  | transmission timeout in seconds |
+------------------+----------+---------------------------------+
| ``content_type`` | ``str``  | type of data to transmit        |
+------------------+----------+---------------------------------+

Notes:

- the node currently supports transmission of json and text data, for which the
  ``content_type`` values are ``application/json`` and ``application/text``
  respectively
- the node will transmit the faw data contained in the payload of the update
  messages it receives, so that should match the transmission data type

``notifier_websocket``
----------------------
A transmission node that transmits data to a websocket endpoint.

+------------------+----------+---------------------------------+
| argument         | type     | description                     |
+==================+==========+=================================+
| ``endpoint``     | ``str``  | destination endpoint            |
+------------------+----------+---------------------------------+

Notes:

- the node sends to its endpoint the serialised content of the update message
  payload, retrieved using ``json.dumps(message.payload)``
- currently, the node reconnects to the destination endpoint every time there
  is a message to transmit, so the connection is not persistent

``videostream_ffmpeg``
----------------------
A transmission node that receives update messages containing frames, and
transmits them over a destination endpoint. Internally, the node creates a
``ffmpeg`` process and whenever an update message is available, writes its
content to the process standard output.

+------------------+----------+---------------------------------+
| argument         | type     | description                     |
+==================+==========+=================================+
| ``dst_host``     | ``str``  | destination host                |
+------------------+----------+---------------------------------+
| ``dst_port``     | ``int``  | destination port                |
+------------------+----------+---------------------------------+
| ``in_width``     | ``int``  | width of the received frame     |
+------------------+----------+---------------------------------+
| ``in_height``    | ``int``  | height of the received frame    |
+------------------+----------+---------------------------------+

Notes:

- this node is still experimental, as many of the options provided to the
  underlying ``ffmpeg`` process are still not included in the configuration

``notifier_udp``
----------------
A transmission node that receives messages containing dictionaries, and
sends them on a simple UDP endpoint. The node fragments the data to send into
smaller chunks, calculating the number of required chunks based on the
maximum payload size available. The sent chunks are encoded using the
encoding specified in the configuration file. If `encode_b64` is set to
true, the data chunks will be encoded in base64.

+------------------+----------+--------------------------------------------+
| argument         | type     | description                                |
+==================+==========+============================================+
| ``endpoint``     | ``str``  | destination host                           |
+------------------+----------+--------------------------------------------+
| ``port``         | ``int``  | destination port                           |
+------------------+----------+--------------------------------------------+
| ``payload_size`` | ``int``  | size in bytes of the message payload       |
+------------------+----------+--------------------------------------------+
| ``max_sequence`` | ``int``  | maximum message sequence number            |
+------------------+----------+--------------------------------------------+
| ``max_chunks``   | ``int``  | maximum frame sequence number              |
+------------------+----------+--------------------------------------------+
| ``encoding``     | ``int``  | data encoding format                       |
+------------------+----------+--------------------------------------------+
| ``encode_b64``   | ``int``  | whether to encode the payload in base64    |
+------------------+----------+--------------------------------------------+

Each transmitted chunk will have the following format::

  {
    "seq": 1,
    "frag": 1,
    "tot": 99,
    "data": ...,
  }

- `seq` is the sequence number of the message being transmitted
- `frag` is the fragment number of the transmitted chunk
- `tot` is the total number of expected chunks for the message
- `data` is the chunk data content