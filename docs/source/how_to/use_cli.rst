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

Remote service
--------------

:bdg-primary:`warp`

Launch the remote service to expose a node for delocalised pipelines to use.

.. code-block:: console

    (.venv) user:~/$ python -m juturna remotize --help
    usage: juturna remotize [-h] --node-name NODE_NAME --node-mark NODE_MARK --plugin-dir PLUGIN_DIR [--pipe-name PIPE_NAME] [--port PORT]
                            [--default-config FILE] [--max-workers MAX_WORKERS]

    options:
      -h, --help            show this help message and exit
      --node-name NODE_NAME, -n NODE_NAME
                            name of the node to run
      --node-mark NODE_MARK, -m NODE_MARK
                            mark of the node to run
      --plugin-dir PLUGIN_DIR, -P PLUGIN_DIR
                            path to plugins directory
      --pipe-name PIPE_NAME, -N PIPE_NAME
                            pipeline name context
      --port PORT, -p PORT  port to listen on
      --default-config FILE, -c FILE
                            default configuration as JSON string
      --max-workers MAX_WORKERS, -w MAX_WORKERS
                            maximum number of worker threads
