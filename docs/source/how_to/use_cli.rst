Use Juturna CLI tools
=====================

Juturna offers a number of CLI tools that provide basic capabilities for
creating and managing pipelines and pipeline components. Some of these tools
come built-in with the basic Juturna installation, whilst others require Juturna
to be installed with specific dependency groups.

The full list of commands (available with the groups ``httpwrapper`` and
``pipebuilder``) can be printed with:

.. code-block:: console

    (.venv) user:~/$ python -m juturna
    usage: juturna [-h] {launch,validate,stub} ...

    Collection of simple CLI utilities to manage pipeline configuration files and pipeline lifecycles.

    options:
      -h, --help            show this help message and exit

    subcommands:
      List of commands included in the juturna CLI

      {launch,validate,stub}
        launch              instantiate and run the pipeline in the configuration file
        validate            scan a configuration file and check its validity
        serve               launch the Juturna pipeline manager service
        create              interactively create new pipeline configuration files
        stub                create a custom node skeleton
        remotize            start the remote node service
        require             collect all the required packages for a pipeline

+--------------+----------------------------+-----------------------------+------------------------------+
| command      | group                      | description                 | dependencies                 |
+==============+============================+=============================+==============================+
| ``launch``   | :bdg-success:`built-in`    | run a target pipeline       | --                           |
+--------------+----------------------------+-----------------------------+------------------------------+
| ``validate`` | :bdg-success:`built-in`    | validate a target pipeline  | --                           |
+--------------+----------------------------+-----------------------------+------------------------------+
| ``create``   | :bdg-primary:`pipebuilder` | create a new pipeline       | ``prompt_toolkit`` |br|      |
|              |                            |                             | ``rich``                     |
+--------------+----------------------------+-----------------------------+------------------------------+
| ``serve``    | :bdg-primary:`httpwrapper` | pipeline manager service    | ``fastapi`` |br|             |
|              |                            |                             | ``fastapi-cli``              |
+--------------+----------------------------+-----------------------------+------------------------------+
| ``stub``     | :bdg-success:`built-in`    | create a custom node stub   | --                           |
+--------------+----------------------------+-----------------------------+------------------------------+
| ``remotize`` | :bdg-primary:`warp`        | remote node service         | ``grpcio`` |br|              |
|              |                            |                             | ``grpcio-tools`` |br|        |
|              |                            |                             | ``protobuf`` |br|            |
|              |                            |                             | ``typing_extensions``        |
+--------------+----------------------------+-----------------------------+------------------------------+
| ``require``  | :bdg-success:`built-in`    | aggregate node requirements | --                           |
+--------------+----------------------------+-----------------------------+------------------------------+

.. |br| raw:: html

     <br>

Pipe launcher
-------------

:bdg-success:`built-in`

Run a pipeline from the command line. The pipeline can be started automatically
after warming up (``--auto``), or the user can be prompted to start and stop.

.. code-block:: console

    (.venv) user:~/$ python -m juturna launch --help
    usage: juturna launch [-h] [--log-level {NOTSET,DEBUG,INFO,WARNING,ERROR}] --config FILE [--auto] [--timeout TIMEOUT] [--dry-gin]

    options:
      -h, --help            show this help message and exit
      --log-level {NOTSET,DEBUG,INFO,WARNING,ERROR}, -l {NOTSET,DEBUG,INFO,WARNING,ERROR}
                            set log level during pipeline execution
      --config FILE, -c FILE
                            pipeline json configuration file
      --auto, -a            start/stop pipeline automatically without prompting the user
      --timeout TIMEOUT, -t TIMEOUT
                            pipeline execution time (in seconds)
      --dry-gin, -d         Graph Instance oNly, do not execute the pipeline

Pipe validator
--------------

:bdg-success:`built-in`

Check a pipeline configuration file for validity.

.. code-block:: console

    (.venv) user:~/$ python -m juturna validate --help
    usage: juturna validate [-h] [--log-level {NOTSET,DEBUG,INFO,WARNING,ERROR}] --config FILE [--deep] [--plugin-folder DIR] [--report FILE]

    options:
      -h, --help            show this help message and exit
      --log-level {NOTSET,DEBUG,INFO,WARNING,ERROR}, -l {NOTSET,DEBUG,INFO,WARNING,ERROR}
                            set log level during pipeline execution
      --config FILE, -c FILE
                            pipeline json configuration file
      --deep, -d            check node config items against their default config files
      --plugin-folder DIR, -p DIR
                            directory where node plugin nodes are stored
      --report FILE, -r FILE
                            save json report of the validation test

Node stub creator
-----------------

:bdg-success:`built-in`

Create a custom node stub.

.. code-block:: console

    (.venv) user:~/$ python -m juturna stub --help
    usage: juturna stub [-h] --node-name NODE_NAME [--node-type NODE_TYPE] [--node-class NODE_CLASS] [--author AUTHOR] [--email EMAIL] [--destination-folder DESTINATION_FOLDER]

    options:
      -h, --help            show this help message and exit
      --node-name NODE_NAME, -n NODE_NAME
                            node name, used for folder and module
      --node-type NODE_TYPE, -t NODE_TYPE
                            node type
      --node-class NODE_CLASS, -N NODE_CLASS
                            node class name, used for class name
      --author AUTHOR, -a AUTHOR
                            node author name
      --email EMAIL, -e EMAIL
                            node author email
      --destination-folder DESTINATION_FOLDER, -d DESTINATION_FOLDER
                            destination folder for the plugin (defaulted to ./plugins)

Dependency aggregator
---------------------

:bdg-success:`built-in`

Aggregate external dependencies of plugin nodes.

.. code-block:: console

    (.venv) user:~/$ python -m juturna require --help
    usage: juturna require [-h] [--log-level {NOTSET,DEBUG,INFO,WARNING,ERROR}] --config FILE
                       --plugin-dir PLUGIN_DIR [PLUGIN_DIR ...] [--add-extra] [--save SAVE]

    options:
      -h, --help            show this help message and exit
      --log-level {NOTSET,DEBUG,INFO,WARNING,ERROR}, -l {NOTSET,DEBUG,INFO,WARNING,ERROR}
                            set log level during pipeline execution
      --config FILE, -c FILE
                            pipeline json configuration file
      --plugin-dir PLUGIN_DIR [PLUGIN_DIR ...], -p PLUGIN_DIR [PLUGIN_DIR ...]
                            plugin folders (at least one is required)
      --add-extra, -a       add collected dependencies to configuration file
      --save SAVE, -s SAVE  where to save the collected dependencies

Pipe creator
------------

:bdg-primary:`pipebuilder`

Interactively create a new pipeline configuration file starting from a set of
plugin folders.

.. code-block:: console

    (.venv) user:~/$ python -m juturna create --help
    usage: juturna create [-h] [--plugins PLUGINS]

    options:
      -h, --help            show this help message and exit
      --plugins PLUGINS, -p PLUGINS
                            juturna service pipeline folder

Pipe service manager
--------------------

:bdg-primary:`httpwrapper`

Launch a pipeline manager that can be queried through HTTP APIs. The manager
allows pipeline manipulation.

.. code-block:: console

    (.venv) user:~/$ python -m juturna serve --help
    usage: juturna serve [-h] --host HOST --port PORT --folder FOLDER [--log-level {NOTSET,DEBUG,INFO,WARNING,ERROR}] [--log-format {simple,colored,full,compact,development,minimal,json}] [--log-file LOG_FILE]

    options:
      -h, --help            show this help message and exit
      --host HOST, -H HOST  juturna service host address
      --port PORT, -p PORT  juturna service port
      --folder FOLDER, -f FOLDER
                            juturna service pipeline folder
      --log-level {NOTSET,DEBUG,INFO,WARNING,ERROR}, -l {NOTSET,DEBUG,INFO,WARNING,ERROR}
                            set log level during pipeline execution
      --log-format {simple,colored,full,compact,development,minimal,json}, -F {simple,colored,full,compact,development,minimal,json}
                            log format
      --log-file LOG_FILE, -L LOG_FILE
                            log file destination

HTTP API of the service
~~~~~~~~~~~~~~~~~~~~~~~

Every request needs the service token, as ``Authorization: Bearer <token>``.
The token is checked before anything else: a request without it is answered
``401`` whatever its path and its body, and this includes the generated
documentation pages (``/docs``, ``/redoc``, ``/openapi.json``). A request body
larger than 1 MiB is answered ``413``.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Request
     - What it does
   * - ``GET /configuration``
     - Version and constants of the service.
   * - ``GET /nodes``
     - The node types installed on the service, each with its ``type`` (the
       name to write in a configuration), its ``description`` and its
       ``arguments`` with their defaults. The nodes are not imported.
   * - ``GET /pipelines``
     - The status of every pipeline.
   * - ``POST /pipelines/validate``
     - Checks a configuration as ``juturna validate`` does and returns the
       report. Nothing is created. Node types are resolved, so their
       packages are imported.
   * - ``POST /pipelines/new``
     - Creates a pipeline from a configuration, and returns its id.
   * - ``POST /pipelines/deploy``
     - Creates, warms up and starts a pipeline. When a step fails, nothing
       is left on the service.
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
     - The telemetry records of the pipeline.

Errors of the service carry a ``message``:

- ``404``: no pipeline with that id, or no such file in its folder;
- ``409``: the call is not allowed in the current status of the pipeline, or
  another lifecycle call is in progress;
- ``403``: the configuration reads an environment variable the service does
  not allow;
- ``422``: the configuration is refused (the body says which part), or a
  warmup or start failed because of a node. In the second case the body also
  has ``operation`` and ``node``, and the message says what the node raised,
  for example a node type that is not installed;
- ``500``: anything else, with the details in the service log.

A configuration is refused when it has no nodes, when a link names a node
that does not exist or is repeated, when a warped node has no
``warp_configuration``, or when ``version`` is empty.

Remote service
--------------

:bdg-primary:`warp`

Launch the remote service to expose a node for delocalised pipelines to use.

.. code-block:: console

    (.venv) user:~/$ python -m juturna remotize --help
    usage: juturna remotize [-h] --node-name NODE_NAME --node-type NODE_TYPE [--pipe-name PIPE_NAME] [--host HOST] [--port PORT]
                            [--default-config FILE] [--max-workers MAX_WORKERS] [--max-requests MAX_REQUESTS] [--max-clients MAX_CLIENTS]
                            [--strict] [--log-level {NOTSET,DEBUG,INFO,WARNING,ERROR}]

    options:
      -h, --help            show this help message and exit
      --node-name, -n NODE_NAME
                            name of the node to run
      --node-type, -t NODE_TYPE
                            type of the node to run
      --pipe-name, -N PIPE_NAME
                            pipeline name context
      --host, -H HOST       address to listen on (default: 127.0.0.1, this machine only). The service has no authentication and no encryption:
                            listen on another address, such as 0.0.0.0 for all of them, on trusted networks only
      --port, -p PORT       port to listen on (default: 50051)
      --default-config, -c FILE
                            default configuration as JSON string
      --max-workers, -w MAX_WORKERS
                            maximum number of worker threads
      --max-requests MAX_REQUESTS
                            requests accepted at once, in progress or waiting for a worker; more are refused (default: 10 for each worker)
      --max-clients MAX_CLIENTS
                            sticky clients the service keeps a state for; new ones are refused beyond that (default: 1024)
      --strict              fail requests with DATA_LOSS instead of leaving out, with a warning, what cannot be sent to the client
      --log-level, -l {NOTSET,DEBUG,INFO,WARNING,ERROR}
                            log level of the service and the node (default: INFO)
