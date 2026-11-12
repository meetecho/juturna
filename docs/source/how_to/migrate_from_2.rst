.. _migrate_from_2:

Upgrade from Juturna 2.x
========================

Juturna 3.0 changes where nodes live, how they are named in a configuration,
and a few parts of the Python API. This guide lists what to change, in the
order you are likely to meet it. Most projects need the first three sections
only.

1. Install the nodes
--------------------

The core library no longer contains nodes, and the hub that downloaded
plugins is gone. The official nodes are now a package of their own:

.. code-block:: console

    (.venv) $ pip install -U juturna juturna-nodes

Not every 2.x node made the move: check the README of
`juturna-nodes <https://github.com/meetecho/juturna_nodes>`_ for the list.
A node that is missing, like any node of your own, has to be ported
(section 3).

2. Update the configuration files
---------------------------------

**Node types.** A node was named by ``type`` (``source``, ``proc``, ``sink``)
and ``mark``. Now ``type`` alone holds the class of the node, and ``mark`` is
gone:

.. code-block:: json

    { "name": "src", "type": "source", "mark": "audio_rtp", "configuration": {} }

becomes

.. code-block:: json

    { "name": "src", "type": "AudioRtp", "configuration": {} }

Some of the nodes you may be using:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - 2.x ``type`` / ``mark``
     - Closest 3.0 ``type``
   * - ``source`` / ``audio_file``
     - ``AudioFile``
   * - ``source`` / ``audio_rtp``, ``audio_rtp_av``
     - ``AudioRtp``
   * - ``source`` / ``video_rtp``, ``video_rtp_av``
     - ``VideoRtp``
   * - ``source`` / ``json_http``
     - ``JsonHTTP``
   * - ``source`` / ``json_websocket``
     - ``JsonWebsocket``
   * - ``proc`` / ``vad_silero``
     - ``VadSilero``
   * - ``proc`` / ``transcriber_whispy``
     - ``TranscriberWhisper``
   * - ``proc`` / ``yolo_detector``
     - ``DetectorYolo``
   * - ``proc`` / ``passthrough_identity``
     - ``PassthroughIdentity``
   * - ``sink`` / ``notifier_http``
     - ``NotifierHTTP``
   * - ``sink`` / ``notifier_udp``
     - ``NotifierUDP``
   * - ``sink`` / ``notifier_mongo``
     - ``NotifierMongo``

The arguments of a node may have changed with it: compare your
``configuration`` with the ``config.toml`` of the new node.

**Plugins.** The top-level ``plugins`` key is ignored: nodes are found among
the installed packages, not in folders. Remove it.

**Telemetry.** ``"telemetry": "file.csv"`` becomes an object:

.. code-block:: json

    "telemetry": { "name": "csv", "target": "file.csv" }

The file is written in the pipeline folder, its name must end with ``.csv``,
and it has one more column (``worker``).

**Synchronisers.** The ``sync`` key of a node is ignored (see section 3).

When you are done, let Juturna check the result:

.. code-block:: console

    (.venv) $ python -m juturna validate --config pipeline.json

3. Port your own nodes
----------------------

**Move them into a package.** Nodes are no longer loaded from a ``plugins``
folder. They live in an installable package, under
``juturna.contrib.<package>.nodes``, and are used with the type
``contrib.<package>.nodes.<Class>``. The quickest way is to create the
skeleton with ``juturna stub`` and move your code in:
:doc:`create_nodes` has the details.

**Accept the state.** ``update()`` now receives the node state as a keyword
argument. A node with the old signature fails on every message:

.. code-block:: python

    # 2.x
    def update(self, message: Message):
        ...

    # 3.0
    def update(self, message: Message, **kwargs):
        ...

**Replace buffers and synchronisers.** The node buffer, the synchronisers and
``next_batch()`` were removed. A node now receives its messages one at a
time, in order of arrival, and ``message.creator`` tells which node sent each
one. A node that waited for a message from each of its inputs keeps the
pending ones in ``kwargs['state']``: there is an example in
:ref:`explain_nodes`.

**Transmit messages only.** ``transmit()`` and source functions deal in
``Message`` objects. Anything else is refused and logged (a source function
can still return ``None`` when it has nothing to deliver).

**Do not change received messages.** Freezing now reaches nested ``meta``
values and the arrays of a payload. To send a received message on with
changes, use ``message.copy()``:

.. code-block:: python

    to_send = message.copy(creator=self.name)
    to_send.meta['checked'] = True

    self.transmit(to_send)

**Removed names.** If your code uses one of these, here is what to do:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Removed
     - Instead
   * - ``juturna.hub`` and the ``JUTURNA_HUB_*``, ``JUTURNA_CACHE_DIR``,
       ``JUTURNA_LOCAL_PLUGIN_DIR``, ``JUTURNA_BASE_REPO`` constants
     - Install node packages with ``pip``.
   * - ``juturna.components.Buffer``, ``Node.clear_buffer()``,
       ``Node.synchroniser``
     - Keep pending messages in the node state.
   * - ``ControlPayload``, ``ControlSignal``,
       ``Pipeline.suspend_node()``, ``Pipeline.resume_node()``
     - No replacement.
   * - ``juturna.utils.proc_utils.safe_exec``
     - Not needed: an exception in ``update()`` is logged and counted, and
       the node goes on.

4. Pipelines in your own code
-----------------------------

- A stopped pipeline cannot be started again. Destroy it and create a new
  one.
- A lifecycle call in the wrong state raises a specific exception
  (``PipelineNotReadyError``, ``PipelineStoppedError``, ...) from
  ``juturna.components``. They all derive from ``RuntimeError``, so existing
  ``except RuntimeError`` blocks keep working.
- ``stop()`` waits for the nodes to finish what they received. The new
  ``kill()`` does not: use it when a node may hang.
- Two ``ObjectPayload`` are now equal when their content is, and an
  ``ObjectPayload`` can no longer be a dictionary key or a set item.

5. Command line
---------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Command
     - What changed
   * - ``require``
     - Removed. The dependencies of a node are those of its package.
   * - ``validate``
     - ``--deep`` and ``--plugin-folder`` are gone: node types and arguments
       are always checked.
   * - ``stub``
     - ``--package`` is required, and the node is created in
       ``./src/juturna/contrib/<package>/nodes``.
   * - ``create``
     - Takes no ``--plugins`` option: it lists the installed nodes.
   * - ``serve``
     - ``--log-level``, ``--log-format`` and ``--log-file`` are replaced by
       ``--log-config``. ``--host`` is optional and defaults to
       ``127.0.0.1``.
   * - ``remotize``
     - ``--node-mark`` is now ``--node-type``, and ``--plugin-dir`` is gone.
       The service listens on ``127.0.0.1`` unless ``--host`` says otherwise.

6. The pipeline service
-----------------------

If you have clients of ``juturna serve``:

- every request needs ``Authorization: Bearer <token>``, with the token of
  the ``JUTURNA_SERVICE_TOKEN`` variable of the service
  (see :doc:`serve_pipelines`);
- a configuration that reads environment variables with ``$JT_ENV_`` is
  refused, unless the variable is in the file given to the service with
  ``--env-file`` or allowed with ``--allow-env`` (see :doc:`environment`);
- a mistake in a request (a broken configuration, a node type that is not
  installed) is answered with a ``4xx`` status and a message, where it often
  was a ``500``.

7. Remote nodes
---------------

- The ``Warp`` node moved to ``juturna-nodes``: install
  ``juturna-nodes[warp]`` where the pipeline runs.
- The remote protocol changed, and is now versioned. Upgrade the pipeline
  side and the remote service together: a 2.x side and a 3.0 side do not
  understand each other.
- The remote service listens on the loopback address by default. A service
  that must be reached from other machines needs ``--host``
  (see :doc:`remotise_node`).
