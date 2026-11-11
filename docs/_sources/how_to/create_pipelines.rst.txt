Write, check and run a pipeline
===============================

This guide shows how to put together a pipeline from nodes that are already
installed, check its configuration, and run it from the command line or from
your own code.

The example uses two nodes of the ``juturna-nodes`` package: ``JsonHTTP``,
which receives JSON documents over HTTP, and ``PassthroughIdentity``, which
forwards what it receives after a delay.

Install the nodes
-----------------

.. code-block:: console

    (.venv) $ pip install juturna-nodes

The README of
`juturna-nodes <https://github.com/meetecho/juturna_nodes>`_ lists the
available nodes and the optional groups some of them need. Every node comes
with a ``config.toml`` file holding its arguments and their defaults.

Write the configuration
-----------------------

Save this as ``echo.json``:

.. code-block:: json

    {
      "version": "3.0.0",
      "pipeline": {
        "name": "http_echo",
        "id": "http_echo_01",
        "folder": "./run",
        "nodes": [
          {
            "name": "receiver",
            "type": "JsonHTTP",
            "configuration": { "port": 8888 }
          },
          {
            "name": "delay",
            "type": "PassthroughIdentity",
            "configuration": { "delay": 1 },
            "auto_dump": true
          }
        ],
        "links": [
          { "from": "receiver", "to": "delay" }
        ]
      }
    }

What to know when writing one:

- ``type`` is the class name for the nodes of ``juturna-nodes``
  (``JsonHTTP``), and the full path for the others
  (``contrib.<package>.nodes.<Class>``);
- ``configuration`` only needs the arguments you want to change;
- ``folder`` is where the pipeline writes its files: a copy of the
  configuration, and one folder per node;
- ``auto_dump`` saves every message a node transmits as a JSON file in its
  folder, handy to see what goes through.

All the keys are described in :ref:`reference_configuration`.

If you prefer to be guided, ``python -m juturna create`` (``pipebuilder``
group) starts an interactive builder: press TAB to pick among the installed
nodes, then use ``.link`` to connect them and ``.save`` to write the file.
``.help`` lists the other commands.

Check it
--------

.. code-block:: console

    (.venv) $ python -m juturna validate --config echo.json

The command checks the structure of the file, that every node type is
installed, that links join existing nodes, and that the graph has no cycles.
It exits with status 1 when a check fails, so it fits in a CI job. Warnings
tell about things that are legal but suspicious, such as a configuration key
the node does not know.

Run it from the command line
----------------------------

.. code-block:: console

    (.venv) $ python -m juturna launch --config echo.json

The pipeline warms up, then waits for you to press enter to start, and again
to stop. With ``--auto`` it starts on its own and runs until every node has
stopped, or for ``--timeout`` seconds.

While it runs, send it something from another terminal:

.. code-block:: console

    $ curl -H 'Content-Type: application/json' \
           -d '{"text": "hello"}' localhost:8888/juturna

A second later the message is in ``./run/delay/``, as a JSON file.

Run it from Python
------------------

A pipeline is a plain object, with one method for each step of its life:

.. code-block:: python

    import time

    import juturna as jt


    pipeline = jt.components.Pipeline.from_json('echo.json')

    pipeline.warmup()
    pipeline.start()

    try:
        time.sleep(60)
    finally:
        pipeline.stop()
        pipeline.destroy()

``Pipeline(config)`` takes the configuration as a dictionary instead of a
file path.

``stop()`` lets the nodes finish the messages they already received. When
that could take too long, ``kill()`` drops them instead:
:ref:`explain_pipelines` tells the two apart.

A stopped pipeline cannot be started again: destroy it, and create a new
one.
