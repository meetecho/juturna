Built-in nodes
==============

Source nodes
------------

Audio file
^^^^^^^^^^

Read an audio file and stream it in small chunks of a configurable length.

Audio RTP
^^^^^^^^^

Consume a remote RTP audio stream. It uses ``ffmpeg`` subprocess.

Audio RTP AV
^^^^^^^^^^^^

Consume a remote RTP audio stream. It uses the ``pyav`` library.

JSON HTTP
^^^^^^^^^

Spawn a HTTP server and reads in received JSON objects.

JSON Websocket
^^^^^^^^^^^^^^

Spawn a websocket server and reads in serialisable objects.

Video file
^^^^^^^^^^

Read a video file and stream it frame by frame.

Video RTP
^^^^^^^^^

Consume a remote RTP video stream. It uses ``ffmpeg`` subprocess.

Video RTP AV
^^^^^^^^^^^^

Consume a remote RTP video stream. It uses the ``pyav`` library.

Sink nodes
----------

Notifier HTTP
^^^^^^^^^^^^^

Send object data to a remote HTTP endpoint.

Notifier UDP
^^^^^^^^^^^^

Send byte data to a remote UDP socket.

Notifier websocket
^^^^^^^^^^^^^^^^^^

Send object data to a remote websocket endpoint.

Videostream ffmpeg
^^^^^^^^^^^^^^^^^^

Stream image payloads on a RTP stream using ``ffmpeg``.
