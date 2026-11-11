.. _tutorial:

Your first pipeline
===================

In this tutorial we build a small pipeline from scratch and run it. It takes
about ten minutes, and needs nothing but Python 3.12 (or newer) and Juturna
itself.

The pipeline has three nodes:

- ``ticker`` produces a line of text every second;
- ``shouter`` turns it into upper case;
- ``printer`` prints it on the terminal.

Along the way we meet the pieces every Juturna project is made of: nodes,
messages, a configuration file, and the command line tools.

Install Juturna
---------------

Create a folder for the project, with a virtual environment in it:

.. code-block:: console

    $ mkdir first-pipeline && cd first-pipeline
    $ python3 -m venv .venv
    $ source .venv/bin/activate
    (.venv) $ pip install juturna

Check that the command line tools answer:

.. code-block:: console

    (.venv) $ python -m juturna --help

You should see the list of commands: ``launch``, ``validate``, ``stub`` and a
few more.

Create the nodes
----------------

A node is a Python class in a package. The ``stub`` command writes the
skeleton for us. We need three nodes, in a package we call ``tutorial``:

.. code-block:: console

    (.venv) $ python -m juturna stub --node-name ticker --package tutorial
    Node creation successful! Node type: contrib.tutorial.nodes.Ticker
    (.venv) $ python -m juturna stub --node-name shouter --package tutorial
    Node creation successful! Node type: contrib.tutorial.nodes.Shouter
    (.venv) $ python -m juturna stub --node-name printer --package tutorial
    Node creation successful! Node type: contrib.tutorial.nodes.Printer

The project now looks like this (a few files are left out):

.. code-block:: text

    src/juturna/contrib/tutorial/nodes/
    ├── __init__.py
    ├── _ticker/
    │   ├── ticker.py
    │   └── config.toml
    ├── _shouter/
    │   ├── shouter.py
    │   └── config.toml
    └── _printer/
        ├── printer.py
        └── config.toml

Each node has its code and a ``config.toml`` file with its arguments. Take
note of the **node types** the command printed: we will need them later.

Python must be able to find the new package. For this tutorial, telling it
where the ``src`` folder is will do:

.. code-block:: console

    (.venv) $ export PYTHONPATH=src

Write the source node
---------------------

The ticker is a *source* node: it has no input, and produces messages on its
own. Declare its arguments, with their default values, in
``src/juturna/contrib/tutorial/nodes/_ticker/config.toml``:

.. code-block:: toml

    [arguments]
    text = "hello"
    interval = 1.0

    [meta]

Then replace the content of ``_ticker/ticker.py`` with:

.. code-block:: python

    from juturna.components import Message
    from juturna.components import Node
    from juturna.payloads import ObjectPayload


    class Ticker(Node[ObjectPayload, ObjectPayload]):
        """Send a line of text at a fixed interval"""

        def __init__(self, text: str, interval: float, **kwargs):
            super().__init__(**kwargs)

            self._text = text
            self._count = 0

            self.set_source(self._tick, by=interval, mode='pre')

        def _tick(self) -> Message[ObjectPayload]:
            self._count += 1

            return Message(
                creator=self.name,
                version=self._count,
                payload=ObjectPayload(text=f'{self._text} {self._count}'),
            )

        def update(self, message: Message[ObjectPayload], **kwargs):
            self.transmit(message)

Three things happen here:

- the arguments of ``config.toml`` arrive in ``__init__``;
- ``set_source`` tells Juturna to call ``_tick`` every ``interval`` seconds;
- every message ``_tick`` returns reaches ``update``, which sends it to the
  next node with ``transmit``.

Write the processing node
-------------------------

The shouter receives a message, and sends a new one. Its ``config.toml``:

.. code-block:: toml

    [arguments]
    suffix = "!"

    [meta]

And ``_shouter/shouter.py``:

.. code-block:: python

    from juturna.components import Message
    from juturna.components import Node
    from juturna.payloads import ObjectPayload


    class Shouter(Node[ObjectPayload, ObjectPayload]):
        """Turn the text it receives into upper case"""

        def __init__(self, suffix: str, **kwargs):
            super().__init__(**kwargs)

            self._suffix = suffix

        def update(self, message: Message[ObjectPayload], **kwargs):
            loud = message.payload['text'].upper() + self._suffix

            to_send = message.copy(creator=self.name)
            to_send.payload = ObjectPayload(text=loud)

            self.transmit(to_send)

A received message cannot be changed, so the node asks for a copy, gives it a
new payload, and transmits that.

Write the sink node
-------------------

The printer is the end of the line: it receives messages and transmits
nothing. It has no arguments, so its ``config.toml`` stays as it is. Replace
``_printer/printer.py`` with:

.. code-block:: python

    from juturna.components import Message
    from juturna.components import Node
    from juturna.payloads import ObjectPayload


    class Printer(Node[ObjectPayload, None]):
        """Print the text it receives"""

        def update(self, message: Message[ObjectPayload], **kwargs):
            print(f'[{message.creator}] {message.payload["text"]}')

Describe the pipeline
---------------------

A pipeline is described by a JSON file: which nodes it has, how they are
configured, and how they are linked. Save this as ``pipeline.json`` in the
project folder:

.. code-block:: json

    {
      "version": "3.0.0",
      "pipeline": {
        "name": "first_pipeline",
        "id": "first_pipeline_01",
        "folder": "./run",
        "nodes": [
          {
            "name": "ticker",
            "type": "contrib.tutorial.nodes.Ticker",
            "configuration": { "text": "juturna says hi" }
          },
          {
            "name": "shouter",
            "type": "contrib.tutorial.nodes.Shouter",
            "configuration": {}
          },
          {
            "name": "printer",
            "type": "contrib.tutorial.nodes.Printer",
            "configuration": {}
          }
        ],
        "links": [
          { "from": "ticker", "to": "shouter" },
          { "from": "shouter", "to": "printer" }
        ]
      }
    }

Each node has a ``name`` of our choice, the ``type`` printed by the ``stub``
command, and a ``configuration`` with the arguments we want to change. The
ticker gets a new ``text``, everything else keeps its default.

Check it
--------

Before running the pipeline, let Juturna check the file:

.. code-block:: console

    (.venv) $ python -m juturna validate --config pipeline.json
    ✓ JSON well formed
    ✓ Configuration structure
    ✓ Nodes well formed
    ✓ Links well formed
    ✓ Valid transport
    ✓ Valid telemetry
    ✓ Node types and arguments
    ✓ DAG properties
    valid

If a check fails, the line says what is wrong: usually a typo in a node type
or in a link.

Run it
------

.. code-block:: console

    (.venv) $ python -m juturna launch --config pipeline.json --auto --timeout 5 --log-level WARNING
    [shouter] JUTURNA SAYS HI 1!
    [shouter] JUTURNA SAYS HI 2!
    [shouter] JUTURNA SAYS HI 3!
    [shouter] JUTURNA SAYS HI 4!

The pipeline starts, runs for five seconds and stops. Run it again without
``--log-level WARNING`` to see what Juturna does meanwhile: it warms the nodes
up, starts them from the last to the first, and stops them from the first to
the last, so that no message is lost.

Change something
----------------

Now make the pipeline yours. In ``pipeline.json``, give the shouter a
different suffix:

.. code-block:: json

    {
      "name": "shouter",
      "type": "contrib.tutorial.nodes.Shouter",
      "configuration": { "suffix": "?!" }
    }

Launch the pipeline again, and the output changes, without touching the code.

What we did
-----------

We wrote three nodes, described a pipeline in a configuration file, checked
it and ran it. Every Juturna pipeline, however large, is made the same way.

From here:

- :doc:`../how_to/create_pipelines` shows how to use the ready-made nodes of
  the ``juturna-nodes`` package, and how to run a pipeline from Python;
- :doc:`../how_to/create_nodes` goes deeper into writing and packaging nodes;
- :doc:`../explain/entities_overview` explains the ideas behind what we just
  built.
