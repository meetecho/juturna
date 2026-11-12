.. _reference_http_api:

HTTP API of the pipeline service
================================

The requests accepted by the service started with ``juturna serve``. For a
guided tour, see :doc:`../how_to/serve_pipelines`.

Authentication
--------------

Every request needs the service token, as ``Authorization: Bearer <token>``.
The token is checked before anything else: a request without it is answered
``401`` whatever its path and its body, and this includes the generated
documentation pages (``/docs``, ``/redoc``, ``/openapi.json``). A request body
larger than 1 MiB is answered ``413``.

The token is the value of the ``JUTURNA_SERVICE_TOKEN`` environment variable
of the service or, when that is not set, the random one the service prints
at startup. With ``--no-auth`` no token is needed.

Requests
--------

Request bodies are JSON. ``{id}`` is the id the service gave the pipeline.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Request
     - What it does
   * - ``GET /configuration``
     - Version of Juturna and the values of some of its
       :ref:`constants <reference_constants>`.
   * - ``GET /nodes``
     - The node types installed on the service, each with its ``type`` (the
       name to write in a configuration), its ``description`` and its
       ``arguments`` with their defaults. The nodes are not imported.
   * - ``GET /pipelines``
     - The status of every pipeline, as ``{"pipelines": [{id: status}]}``:
       a list with one object, keyed by pipeline id.
   * - ``POST /pipelines/validate``
     - Checks a configuration as ``juturna validate`` does and returns the
       report. Nothing is created. Node types are resolved, so their
       packages are imported.
   * - ``POST /pipelines/new``
     - Creates a pipeline from a configuration. Its id is in
       ``data.pipeline_id`` of the answer. The ``id`` and ``folder`` of the
       configuration are replaced by the ones the service assigns.
   * - ``POST /pipelines/deploy``
     - Creates, warms up and starts a pipeline, and answers with its status
       (the id is ``pipe_id``). When a step fails, nothing is left on the
       service.
   * - ``POST /pipelines/{id}/warmup``, ``/start``, ``/stop``
     - Lifecycle calls. They answer with the status, when the call is over.
   * - ``POST /pipelines/{id}/delete``
     - Destroys the pipeline; ``?wipe=true`` also removes its folder.
   * - ``GET /pipelines/{id}/status``
     - Name, creation time, folder and status of the pipeline, and status
       and ``health`` of each node. ``health`` includes ``last_failure``, the
       most recent error of the node.
   * - ``GET /pipelines/{id}/config``
     - The configuration the pipeline was created with, plus the ``id`` and
       ``folder`` the service gave it. Top-level keys the service does not
       use (``plugins``) are kept.
   * - ``GET /pipelines/{id}/files``
     - The files in the pipeline folder: ``path``, ``size`` and ``modified``.
   * - ``GET /pipelines/{id}/files/{path}``
     - The content of one of those files, always as a download. Only files
       inside the pipeline folder can be read.
   * - ``GET /pipelines/{id}/logs``
     - The last 1000 log records of the pipeline and of its nodes;
       ``?since=<unix time>`` returns the ones after that time. Records
       below the log level of the service are not kept: without a log
       configuration that sets another level, these are warnings and
       errors. Pipelines with the same name share their records.
   * - ``GET /pipelines/{id}/telemetry``
     - The telemetry records of the pipeline, if its configuration turns
       telemetry on.

Errors
------

Errors of the service carry a ``message`` (the ``401`` and ``413`` answers
carry a ``detail`` instead):

- ``404``: no pipeline with that id, or no such file in its folder;
- ``409``: the call is not allowed in the current status of the pipeline, or
  another lifecycle call is in progress;
- ``403``: the configuration reads an environment variable that is neither
  in the environment file of the service nor allowed by it;
- ``422``: the configuration is refused (the body says which part), or a
  warmup or start failed because of a node. In the second case the body also
  has ``operation`` and ``node``, and the message says what the node raised,
  for example a node type that is not installed;
- ``500``: anything else, with the details in the service log.

A configuration is refused when it has no nodes, when a link names a node
that does not exist or is repeated, when a warped node has no
``warp_configuration``, or when ``version`` is empty.
