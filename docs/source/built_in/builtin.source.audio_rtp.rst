``AudioRTP``
============

This node consumes a remote RTP audio stream through ``ffmpeg`` subprocess, and
produces audio messages, each one containing an audio payload of a configured
temporal length. The heavy lifting of reading the incoming stream, buffering it
and converting its content to raw audio is then completely delegated to
``ffmpeg``.

Internally, the node launches the subprocess through a script, and then manages
its lifecycle through a monitor thread.

Launching the script requires 2 distinct files: a sdp template, and the actual
script template. The first one looks like this:

.. code-block:: text

    v=0
    o=- 0 0 IN IP4 $_remote_rtp_host
    s=No Name
    c=IN IP4 $_remote_rtp_host
    t=0 0
    a=tool:libavformat 58.76.100
    m=audio $_remote_rtp_port RTP/AVP $_remote_payload_type
    a=rtpmap:$_remote_payload_type $_encoding_clock_chan
    a=fmtp:$_remote_payload_type sprop-stereo=1

The ``ffmpeg`` script template contains the following:

.. code-block:: bash

    ffmpeg \
        -protocol_whitelist file,rtp,udp \
        -i $_sdp_location \
        -f s16le \
        -ac $_channels \
        -acodec pcm_s16le \
        -ar $_audio_rate \
        -loglevel $_process_log_level \
        pipe:

They both get compiled when the node is warmed up, and stored in the node
folder. Once the node starts, the monitor thread will look after the subprocess.
This is needed as ``ffmpeg`` might hang or stop when the remote source is not
producing any data for a while.

Arguments
---------

``rec_host : str = "127.0.0.1"``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Hostname of the remote RTP sender.

``rec_port : int = 0``

Port the remote RTP sender is transmitting the audio to. If set to 0, the port
will be assigned automatically by the resource broker.

``audio_rate : int = 16000``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Internal audio sampling rate, in Hz. This determines the number of samples per
second that will be produced by the node.

``block_size : int = 3``
^^^^^^^^^^^^^^^^^^^^^^^^

Size of the audio block to generate, in seconds.

``channels : int = 2``
^^^^^^^^^^^^^^^^^^^^^^

Number of channels in the incoming RTP audio stream.

``process_log_level : str = "quiet"``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Logging level of the internal ``ffmpeg`` subprocess.

``payload_type : int = 97``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Payload type of the incoming RTP audio stream.

``encoding_clock_chan : str = "opus/48000/2"``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Encoding name, clock rate and channels for the RTP stream, as defined in
`RFC 4566 <https://datatracker.ietf.org/doc/html/rfc4566>`_ (SDP) and in
`RFC 3555 <https://datatracker.ietf.org/doc/html/rfc3555>`_ (MIME type
registration for RTP payload formats).
