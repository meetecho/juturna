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
the stream on a port picked at runtime and make it available to a local RTP
client.

+------------------+----------+----------------------------------------+
| argument         | type     | description                            |
+==================+==========+========================================+
| ``rec_host``     | ``str``  | the host from which the stream will be |
|                  |          | received                               |
+------------------+----------+----------------------------------------+
| ``trx_host``     | ``str``  | the host of the local RTP client       |
|                  |          | (usually ``127.0.0.1``)                |
+------------------+----------+----------------------------------------+
| ``audio_rate``   | ``int``  | rate of the receiving audio            |
+------------------+----------+----------------------------------------+
|  ``block_size``  | ``int``  | length (in seconds) of the audio chunks|
|                  |          | to generate                            |
+------------------+----------+----------------------------------------+
|  ``channels``    | ``int``  | number of channels of the receiving    |
|                  |          | audio                                  |
+------------------+----------+----------------------------------------+
| ``payload_type`` | ``dict`` | payload type as specified in the       |
|                  |          | incoming stream                        |
+------------------+----------+----------------------------------------+

During the warmup phase, this node will write in its node folder the sdp file
with all the relevant information about the local stream.

Nodes:

- this node accumulates audio samples until the temporal length of all the
  samples reach ``block_size``, computed in seconds; this length is computed
  using ``audio_rate``, so make sure it matches the sources'

``video_rtp``
-------------
This node consumes a remote RTP video stream, and makes it available to its
destinations as either individual frames or collections of frames, depending on
its working mode. Internally, it uses ``opencv-python`` to open the generated
sdp file.

+------------------+----------+----------------------------------------+
| argument         | type     | description                            |
+==================+==========+========================================+
| ``rec_host``     | ``str``  | the host from which the stream will be |
|                  |          | received                               |
+------------------+----------+----------------------------------------+
| ``trx_host``     | ``str``  | the host of the local RTP client       |
|                  |          | (usually ``127.0.0.1``)                |
+------------------+----------+----------------------------------------+
| ``audio_rate``   | ``int``  | rate of the receiving audio            |
+------------------+----------+----------------------------------------+
|  ``block_size``  | ``int``  | length (in seconds) of the audio chunks|
|                  |          | to generate                            |
+------------------+----------+----------------------------------------+
|  ``channels``    | ``int``  | number of channels of the receiving    |
|                  |          | audio                                  |
+------------------+----------+----------------------------------------+
| ``payload_type`` | ``dict`` | payload type as specified in the       |
|                  |          | incoming stream                        |
+------------------+----------+----------------------------------------+

  * ``audio_file``
* ``video_local``
* ``data_websocket`` (to develop later)

Sink
====

* ``notifier_http``
* ``notifier_websocket``
* ``notifier_mongo`` (suspend for now)
* ``videostream_ffmpeg``
* ``audiostream_ffmpeg`` (to develop later - check at least 20ms per sample)
