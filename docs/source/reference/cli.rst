.. _reference_cli:

Command line tools
==================

Juturna is run as a Python module:

.. code-block:: console

    (.venv) $ python -m juturna <command> [options]

``python -m juturna --help`` lists the commands, and
``python -m juturna <command> --help`` the options of each.

+--------------+----------------------------+----------------------------------------------+
| command      | group                      | what it does                                 |
+==============+============================+==============================================+
| ``launch``   | :bdg-success:`core`        | run a pipeline from its configuration file   |
+--------------+----------------------------+----------------------------------------------+
| ``validate`` | :bdg-success:`core`        | check a configuration file                   |
+--------------+----------------------------+----------------------------------------------+
| ``stub``     | :bdg-success:`core`        | create the skeleton of a node                |
+--------------+----------------------------+----------------------------------------------+
| ``create``   | :bdg-primary:`pipebuilder` | build a configuration file interactively     |
+--------------+----------------------------+----------------------------------------------+
| ``serve``    | :bdg-primary:`httpwrapper` | start the pipeline service                   |
+--------------+----------------------------+----------------------------------------------+
| ``remotize`` | :bdg-primary:`warp`        | start the remote node service                |
+--------------+----------------------------+----------------------------------------------+

Commands of a group other than ``core`` are available when Juturna is
installed with that optional group (see :doc:`../how_to/install`).

launch
------

Run a pipeline. Without ``--auto``, the command waits for enter before
starting the pipeline, and again before stopping it.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Option
     - Meaning
   * - ``--config``, ``-c`` ``FILE``
     - The pipeline configuration file. Required.
   * - ``--auto``, ``-a``
     - Start without prompting. The pipeline runs until all its nodes have
       stopped, or for ``--timeout`` seconds.
   * - ``--timeout``, ``-t`` ``SECONDS``
     - With ``--auto``, stop the pipeline after this time.
   * - ``--dry-gin``, ``-d``
     - Graph Instance oNly: build and warm up the nodes, then destroy the
       pipeline without running it.
   * - ``--log-level``, ``-l`` ``LEVEL``
     - ``NOTSET``, ``DEBUG`` (default), ``INFO``, ``WARNING`` or ``ERROR``.

validate
--------

Check a configuration file without building any node. The checks, in order:
the JSON is well formed, the structure is right, nodes and links are well
formed, transport and telemetry are valid, node types are installed and
accept their configuration, the graph has no cycle.

The command prints one line per check, with warnings below it, then ``valid``
or ``invalid``. It exits with status 0 when every check passes, 1 otherwise.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Option
     - Meaning
   * - ``--config``, ``-c`` ``FILE``
     - The pipeline configuration file. Required.
   * - ``--report``, ``-r`` ``FILE``
     - Also save the results as JSON: every check with its outcome, error
       and warnings, and the layers of the graph.
   * - ``--log-level``, ``-l`` ``LEVEL``
     - As in ``launch``.

stub
----

Create the skeleton of a node in
``<destination>/juturna/contrib/<package>/nodes/_<node name>/`` and register
it in the ``__init__.py`` of the nodes package. Run it from the root of a
node repository.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Option
     - Meaning
   * - ``--node-name``, ``-n`` ``NAME``
     - Name of the node folder and module, in snake case. Required.
   * - ``--package``, ``-p`` ``NAME``
     - The contrib package the node belongs to. Required.
   * - ``--node-class``, ``-N`` ``NAME``
     - Class name. By default the node name in camel case
       (``red_cat_detector`` becomes ``RedCatDetector``).
   * - ``--author``, ``-a``, ``--email``, ``-e``
     - Written in the header of the node file.
   * - ``--destination-folder``, ``-d`` ``DIR``
     - Source folder of the repository. Default: ``./src``.

create
------

Start the interactive pipeline builder, which lists the nodes installed in
the ``juturna.nodes``, ``juturna.extensions`` and ``juturna.contrib``
namespaces. It takes no options. Inside the builder, ``.help`` lists the
commands.

serve
-----

Start the pipeline service. See :doc:`../how_to/serve_pipelines` and
:ref:`reference_http_api`.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Option
     - Meaning
   * - ``--port``, ``-p`` ``PORT``
     - Port to listen on. Required.
   * - ``--folder``, ``-f`` ``DIR``
     - Where the pipelines keep their folders. Required.
   * - ``--host``, ``-H`` ``ADDRESS``
     - Address to listen on. Default: ``127.0.0.1``.
   * - ``--log-config``, ``-l`` ``FILE``
     - Logging configuration, a JSON file for ``logging.config.dictConfig``.
   * - ``--allow-env``, ``-e`` ``NAME``
     - An environment variable that configurations can read with
       ``$JT_ENV_``. Repeat it for each variable; none by default.
   * - ``--dev``, ``-d``
     - Development mode: allow cross-origin requests.
   * - ``--no-auth``
     - Do not require the service token.

The token is read from the ``JUTURNA_SERVICE_TOKEN`` environment variable.
When it is not set, a random one is printed at startup.

remotize
--------

Start the remote node service: one node, served over gRPC to the warp nodes
of other pipelines. See :doc:`../how_to/remotise_node` and
:ref:`explain_remote`.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Option
     - Meaning
   * - ``--node-name``, ``-n`` ``NAME``
     - Name given to the node. Required.
   * - ``--node-type``, ``-t`` ``TYPE``
     - Type of the node, as in a pipeline configuration. Required.
   * - ``--default-config``, ``-c`` ``FILE``
     - JSON file with the configuration of the node.
   * - ``--pipe-name``, ``-N`` ``NAME``
     - Pipeline name the node logs under.
   * - ``--host``, ``-H`` ``ADDRESS``
     - Address to listen on. Default: ``127.0.0.1``. The service has no
       authentication and no encryption: use another address on trusted
       networks only.
   * - ``--port``, ``-p`` ``PORT``
     - Port to listen on. Default: ``50051``.
   * - ``--max-workers``, ``-w`` ``N``
     - Worker threads. Default: 10.
   * - ``--max-requests`` ``N``
     - Requests accepted at once, in progress or waiting for a worker.
       Default: 10 for each worker.
   * - ``--max-clients`` ``N``
     - Sticky warp nodes the service keeps a state for. Default: 1024.
   * - ``--strict``
     - Fail a request with ``DATA_LOSS`` when something cannot be sent back
       to the client, instead of leaving it out with a warning.
   * - ``--log-level``, ``-l`` ``LEVEL``
     - Log level of the service and the node. Default: ``INFO``.

The command exits with status 1 when the node cannot be built or the address
is already in use.
