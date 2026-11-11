Observe a pipeline
==================

This guide shows how to see what a running pipeline is doing: its logs, the
health of its nodes, telemetry records, and the files it writes.

Logging
-------

Nodes have a built-in logger that can be used straight out of the box. A node
logger is created as a sublogger of its containing pipeline, which in turn is
a sublogger of the juturna process. Nothing special is required to use the
juturna logger within a node, and it can be used anywhere in its class code:

.. code-block:: python

    from juturna.components import Node
    from juturna.components import Message
    from juturna.payloads import BasePayload


    class MyAwesomeNode(Node[BasePayload, BasePayload]):
        def __init__(self, *args, **kwargs):
            super().__init__(**kwargs)

            # initialisation code

            self.logger.info('awesome node created!')

        def update(self, message: Message[BasePayload], **kwargs):
            # run the node update logic

            self.logger.info('node did something awesome!')

Logging messages will carry useful pieces of information so that, once printed,
it will be easy to understand which entry is printed by which node. As an
example, consider the script below, loading a pipe called ``my_pipe``:

.. code-block:: python

    import logging

    import juturna as jt


    jt.log.jt_logger().setLevel(logging.DEBUG)

    pipe = jt.components.Pipeline.from_json('config.json')
    pipe.warmup()

This will generate logging entries split by node:

.. code-block:: console

    2026-02-12 15:05:20 | INFO     | jt.my_pipe.node_0       | init sources: []
    2026-02-12 15:03:54 | INFO     | jt.my_pipe.node_0       | trx created, model id 123197287926000
    2026-02-12 15:03:55 | INFO     | jt.my_pipe.node_1       | audio loaded
    2026-02-12 15:03:55 | INFO     | jt.my_pipe.node_1       | duration: 149.942875
    2026-02-12 15:03:55 | INFO     | jt.my_pipe              | warmed up node node_0
    2026-02-12 15:03:55 | ERROR    | jt.my_pipe.node_1       | model not found, defaulting
    2026-02-12 15:03:55 | INFO     | jt.my_pipe              | warmed up node node_1
    2026-02-12 15:03:55 | INFO     | jt.my_pipe              | warmed up node node_2
    2026-02-12 15:03:55 | INFO     | jt.my_pipe.node_3       | endpoint reached
    2026-02-12 15:03:55 | INFO     | jt.my_pipe              | warmed up node node_3
    2026-02-12 15:03:55 | INFO     | jt.my_pipe              | pipe warmed up!

Here we can see that each entry tells us the node that generated it, the pipe it
belongs to, and lastly the logging message.

Thanks to their hierarchical structure, loggers can be selectively enabled or
disabled through the names of their corresponding components. Looking again
at the pipe above, we can tell the loggers to raise the level to ``ERROR`` only
for ``node_1``:

.. code-block:: python

    import logging

    import juturna as jt

    jt.log.jt_logger().setLevel(logging.DEBUG)
    jt.log.jt_logger('my_pipe.node_1').setLevel(logging.ERROR)

    pipe = jt.components.Pipeline.from_json('config.json')
    pipe.warmup()

This time, the logs will look like:

.. code-block:: console

    2026-02-12 15:05:20 | INFO     | jt.my_pipe.node_0       | init sources: []
    2026-02-12 15:03:54 | INFO     | jt.my_pipe.node_0       | trx created, model id 123197287926000
    2026-02-12 15:03:55 | INFO     | jt.my_pipe              | warmed up node node_0
    2026-02-12 15:03:55 | ERROR    | jt.my_pipe.node_1       | model not found, defaulting
    2026-02-12 15:03:55 | INFO     | jt.my_pipe              | warmed up node node_1
    2026-02-12 15:03:55 | INFO     | jt.my_pipe              | warmed up node node_2
    2026-02-12 15:03:55 | INFO     | jt.my_pipe.node_3       | endpoint reached
    2026-02-12 15:03:55 | INFO     | jt.my_pipe              | warmed up node node_3
    2026-02-12 15:03:55 | INFO     | jt.my_pipe              | pipe warmed up!

Formatters and handlers
^^^^^^^^^^^^^^^^^^^^^^^

Logs in juturna can be formatted using built-in formatters: ``simple``,
``colored``, ``full`` (default), ``compact``, ``development``, ``minimal`` and
``json``. To change it, run:

.. code-block:: python

    import logging

    import juturna as jt


    jt.log.jt_logger().setLevel(logging.DEBUG)
    jt.log.formatter('minimal')

    pipe = jt.components.Pipeline.from_json('config.json')
    pipe.warmup()

.. code-block:: console

    INFO: init sources: []
    INFO: trx created, model id 123197287926000
    INFO: audio loaded
    INFO: duration: 149.942875
    INFO: warmed up node node_0
    ERROR: model not found, defaulting
    INFO: warmed up node node_1
    INFO: warmed up node node_2
    INFO: endpoint reached
    INFO: warmed up node node_3
    INFO: pipe warmed up!

New handlers can also be added to the juturna logger. As an example, a file
handler can be added, to store the logs into a file:

.. code-block:: python

    import logging

    import juturna as jt


    handler = logging.FileHandler('juturna.log')

    jt.log.add_handler(handler, formatter='development')

Health
------

Every node counts its failures. ``pipeline.status`` returns them, with the
state of the pipeline and of each node:

.. code-block:: python

    >>> pipe.status['nodes']['node_1']['health']
    {'update_failures': 1,
     'worker_failures': 0,
     'source_failures': 0,
     'rejected_items': 0,
     'last_failure_at': 1794437137.17,
     'last_failure': 'ValueError: model not found',
     'stuck_workers': []}

- ``update_failures`` and ``source_failures`` count the exceptions raised by
  ``update()`` and by the source function. The node logs them and goes on.
- ``rejected_items`` counts the things that were not a ``Message`` and were
  refused.
- ``last_failure`` is the most recent error; the traceback is in the log.
- ``stuck_workers`` lists the threads that did not exit when the node was
  killed.

The pipeline service returns the same data from
``GET /pipelines/{id}/status``.

Telemetry
---------

Telemetry records when each node receives and transmits a message. From the
records you can work out latency and throughput of every node, and follow a
message through the pipeline.

Turn it on in the pipeline configuration, choosing where the records go:

.. code-block:: json

    {
      "version": "3.0.0",
      "pipeline": {
        "name": "my_pipe",
        "id": "123456",
        "folder": "./run",
        "telemetry": { "name": "csv", "target": "telemetry.csv" },
        "nodes": [],
        "links": []
      }
    }

With the ``csv`` manager, the file ``./run/telemetry.csv`` fills up while the
pipeline runs:

.. code-block:: text

    ts,evt,node,origin,msg_id,src_id,size,worker
    1794437137.17,rx,A,A,0,,5,main
    1794437137.17,tx,A,A,0,0,5,main
    1794437137.18,rx,B,A,0,0,5,main
    1794437138.18,tx,B,B,1,0,12,main

Reading the four lines: source node ``A`` received its own message 0 and
transmitted it; node ``B`` received it and, a second later, transmitted
message 1, made while processing message 0 (``src_id``).

Use ``{"name": "memory"}`` to keep the records in memory instead, which is
what the pipeline service needs to return them from
``GET /pipelines/{id}/telemetry``.

The managers, their options and the meaning of every field are in
:ref:`reference_configuration`.

Files
-----

Each node has a folder of its own inside the pipeline folder, named after the
node. Its path is ``self.pipe_path``:

.. code-block:: python

    def update(self, message: Message, **kwargs):
        with open(pathlib.Path(self.pipe_path, 'notes.txt'), 'a') as f:
            f.write('saving another entry\n')

``self.dump_json(message, 'file_name.json')`` writes a message there as JSON.
To save every message a node transmits without touching its code, add
``"auto_dump": true`` to the node in the pipeline configuration:

.. code-block:: json

    {
      "name": "node_name",
      "type": "PassthroughIdentity",
      "auto_dump": true,
      "configuration": {}
    }
