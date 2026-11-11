.. _reference_configuration:

Pipeline configuration file
===========================

A pipeline is described by a JSON document. This page lists every key
Juturna reads.

.. code-block:: json

    {
      "version": "3.0.0",
      "pipeline": {
        "name": "my_pipeline",
        "id": "my_pipeline_01",
        "folder": "./run",
        "telemetry": { "name": "csv", "target": "telemetry.csv" },
        "nodes": [
          {
            "name": "source",
            "type": "AudioFile",
            "configuration": {}
          },
          {
            "name": "sink",
            "type": "contrib.acme.nodes.MySink",
            "configuration": { "endpoint": "$JT_ENV_SINK_URL" },
            "auto_dump": true
          }
        ],
        "links": [
          { "from": "source", "to": "sink" }
        ]
      }
    }

Top level
---------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Key
     - Required
     - Meaning
   * - ``version``
     - service only
     - The Juturna version the file was written for. The pipeline service
       refuses a configuration without it; nothing else reads it yet.
   * - ``pipeline``
     - yes
     - The pipeline, described below.

Other top-level keys are ignored.

``pipeline``
------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Key
     - Required
     - Meaning
   * - ``name``
     - yes
     - Name of the pipeline, used by its loggers (``jt.<name>``).
   * - ``id``
     - yes
     - Identifier of the pipeline. The pipeline service replaces it with one
       of its own.
   * - ``folder``
     - yes
     - Folder of the pipeline, created at warm up. It receives a copy of the
       configuration (``config.json``) and one folder per node. The pipeline
       service replaces it with a folder of its own.
   * - ``nodes``
     - yes
     - List of nodes, see below.
   * - ``links``
     - yes
     - List of links, see below.
   * - ``telemetry``
     - no
     - Turns telemetry on, see below.
   * - ``transport``
     - no
     - How nodes run and exchange messages: ``"threading"`` (default) or
       ``"browser"``, for pipelines running in a web page with Pyodide. It
       can also be an object with the ``name`` and the options of the
       transport.
   * - ``log_extra``
     - no
     - Object whose entries are added to every log record of the pipeline,
       for formatters that print them (such as ``json``).

``nodes``
---------

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Key
     - Required
     - Meaning
   * - ``name``
     - yes
     - Name of the node, unique in the pipeline. It becomes a folder name:
       up to 128 letters, digits, ``_``, ``-`` and ``.``, not starting with
       ``-`` or ``.``.
   * - ``type``
     - yes
     - The node class. A bare class name (``AudioFile``) is looked up in
       ``juturna.nodes``, the namespace of the ``juturna-nodes`` package. A
       path starting with ``contrib.`` or ``extensions.`` is looked up under
       ``juturna``: ``contrib.acme.nodes.MySink`` is the class ``MySink`` of
       ``juturna.contrib.acme.nodes``.
   * - ``configuration``
     - yes
     - Arguments of the node, overriding the defaults of its
       ``config.toml``. It can be empty. Keys the node does not declare are
       ignored. A string value starting with ``$JT_ENV_`` is replaced by
       the environment variable of that name
       (see :doc:`../how_to/environment`).
   * - ``auto_dump``
     - no
     - When ``true``, every message the node transmits is saved in its
       folder as ``auto_<message id>.json``.
   * - ``warped``
     - no
     - When ``true``, the node runs in a remote service and a ``Warp`` node
       takes its place in the pipeline
       (see :doc:`../how_to/remotise_node`).
   * - ``warp_configuration``
     - if warped
     - Configuration of the ``Warp`` node: ``grpc_host``, ``grpc_port``,
       ``timeout``.
   * - ``sticky``
     - no
     - For a warped node, where its state lives: on the remote service
       (``true``, default) or with the warp node (``false``).
   * - ``worker``
     - no
     - The worker the node runs in, for transports with several workers
       (``browser``). Default: ``main``.

``links``
---------

Each link is an object with ``from`` and ``to``, the names of two nodes.
Messages transmitted by ``from`` are delivered to ``to``. A node can have
several links in each direction. A link cannot be repeated, and the links
cannot form a cycle.

``telemetry``
-------------

An object with the ``name`` of a telemetry manager and its options. Without
this key, telemetry is off.

.. list-table::
   :header-rows: 1
   :widths: 15 30 55

   * - ``name``
     - Options
     - What it does
   * - ``csv``
     - ``target`` (required), ``max_pending`` (default 10000)
     - Writes the records to the file ``target``, a name ending in
       ``.csv``, in the pipeline folder. ``max_pending`` is how many batches
       can wait to be written before new ones are dropped.
   * - ``memory``
     - ``max_records`` (default 10000)
     - Keeps the latest records in memory. The pipeline service returns
       them from its telemetry endpoint.
   * - ``browser``
     - ``max_records`` (default 10000)
     - Like ``memory``, and posts every batch to the page hosting the
       pipeline. Needs the ``browser`` transport.

A record has these fields, in this order:

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Field
     - Meaning
   * - ``ts``
     - When the event was recorded, as a Unix timestamp.
   * - ``evt``
     - ``rx`` when the node received a message, ``tx`` when it transmitted
       one.
   * - ``node``
     - The node recording the event.
   * - ``origin``
     - The node that created the message.
   * - ``msg_id``
     - Id of the message.
   * - ``src_id``
     - Id of the message its creator was processing when it transmitted
       this one, which links an output to the input it comes from. Empty
       for a message that was not transmitted yet.
   * - ``size``
     - Size of the payload in bytes, 0 when the payload has no size.
   * - ``worker``
     - The worker the node runs in.
