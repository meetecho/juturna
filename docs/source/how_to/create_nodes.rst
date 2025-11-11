Create custom nodes
===================

This guide contains the basic instructions you can follow to create a custom
node to use within Juturna pipelines. Other than an overview of how to assemble
all the pieces to design useful custom components, this document will offer the
required steps to create a custom processing node called ``RedCatDetector``. a
proc node in charge of using a custom YOLO model to detect the presence of a
red cat in any input images.

Setup the environment
---------------------

Make sure you are working on a virtual environment, and you have Juturna
installed alongside all the extra dependencies you need for your node.

.. code-block:: console

    user:~/prj$ python3 -m venv .venv
    user:~/prj$ source .venv/bin/activate
    (.venv) user:~/prj$ git clone https://github.com/meetecho/juturna
    (.venv) user:~/prj$ pip install ./juturna

As we might be interested in using Juturna community plugins, the corresponding
folder can be moved from the cloned Juturna repository to the root of the
project:

.. code-block:: console

    (.venv) user:~/prj$ cp -r ./juturna/plugins ./

Nodes will then be available in ``./juturna/plugins/nodes``.

Create the node skeleton
------------------------

Every node has the same base content structure. A node called ``<NODE_NAME>`` of
type ``<NODE_TYPE>`` will be stored as:

.. code-block::

  ./plugins
    └── nodes
        └── <NODE_TYPE>
            └── _<NODE_NAME>
                ├── <NODE_NAME>.py
                ├── config.toml
                ├── requirements.txt
                └── readme.md

Since ``MyAwesomeNode`` is a proc node, we can go ahead and create all the
required files under ``./plugins/nodes/proc/_red_cat_detector/``. Alternatively,
we can let Juturna handle that for us with the CLI ``stub`` command:

.. code-block:: console

    (.venv) user:~/prj$ python -m juturna stub \
                               -n red_cat_detector \
                               -t proc \
                               -d ./plugins/nodes \
                               -a "Cat Watcher" \
                               -e watch@cat.com

This will generate a node skeleton.

.. tab-set::

    .. tab-item:: red_cat_detector.py

        .. code-block:: python

            """
            RedCatDetector

            @author: Cat Watcher
            @email: watch@cat.com
            @created_at: 2025-11-10 12:56

            Automatically generated with jt.utils.node_utils.node_stub
            """
            import typing

            from juturna.components import Node
            from juturna.components import Message

            # BasePayload type is intended to be a placehoder for the input-output types
            # you intend to use in the node implementation
            from juturna.payloads._payloads import BasePayload


            class RedCatDetector(Node[BasePayload, BasePayload]):
                """Node implementation class"""

                def __init__(self, **kwargs):
                    """
                    Parameters
                    ----------
                    kwargs : dict
                        Supernode arguments.

                    """
                    super().__init__(**kwargs)

                def configure(self):
                    """Configure the node"""
                    ...

                def warmup(self):
                    """Warmup the node"""
                    ...

                def set_on_config(self, prop: str, value: typing.Any):
                    """Hot-swap node properties"""
                    ...

                def start(self):
                    """Start the node"""
                    # after custom start code, invoke base node start
                    super().start()

                def stop(self):
                    """Stop the node"""
                    # after custom stop code, invoke base node stop
                    super().stop()

                def destroy(self):
                    """Destroy the node"""
                    ...

                def update(self, message: Message[BasePayload]):
                    """Receive data from upstream, transmit data downstream"""
                    ...

                # uncomment next_batch to design custom synchronisation policy
                # def next_batch(sources: dict) -> dict:
                #     ...

    .. tab-item:: config.toml

        .. code-block:: toml

            [arguments]

            [meta]

    .. tab-item:: README.md

        .. code-block:: markdown

            # red_cat_detector

            ## Node type: proc

            ## Node class name: RedCatDetector

            ## Node name: red_cat_detector

    .. tab-item:: requirements.txt

        .. code-block:: text

            // this file is empty

If you decide to create your node files manually:

- make sure the node folder name starts with an underscore (``_``)
- make sure the node class file has the same name of its parent folder, just
  without the underscore
- keep in mind that a ``README.md`` file is not required, but **higly
  recommended!**

Add dependencies
----------------

We know our node will use a custom `YOLO <https://docs.ultralytics.com/>`_ model
to detect the presence of red cats, so when executing the pipeline we need to
make sure all the YOLO dependencies are satisfied. We then install the
``ultralytics`` package, and make sure to include it in the requirement file.

.. code-block:: text

    ultralytics==8.3.79

.. admonition:: Dependencies are not automatically managed (|version|-|release|)
    :class: :ATTENTION:

    Juturna does not manage Python dependencies automatically, so always
    remember to gather the dependencies of any plugin nodes you want to use, and
    install them. This process may also lead to conflicts; if that happens, you
    can try to solve them manually, or in the worst case, edit the conflicting
    nodes or create new ones!

Add configuration items
-----------------------

For our red cat detector, we want to specify a few arguments that will be
available for the node implementation.

First of all, we need to specify the name of the model to be used during
inference. Being a custom model, it will very likely be local, stored somewhere
on the filesystem. We can also specify the device the model will run on (it
could be a CPU or a GPU), and the minimum threshold confidence we expect to
achieve to mark something as a red cat.

All this can be packed in the node configuration file, where we can define the
node arguments and their corresponding default values.

.. code-block:: toml

    [arguments]
    model = "./red_cat.pt"
    device = "cuda"
    confidence = 0.4

Implement the node
------------------

The items specified in the node config file are also available to the node
``__init__`` method. We start implementing the node class:

- we import the node dependencies (in this case, only ``ultralytics``),
- we modify the constructor signature to include the node arguments,
- we change the input and output types for the node

.. code-block:: python

    from ultralytics import YOLO

    from juturna.payloads._payloads import ImagePayload


    class RedCatDetector(Node[ImagePayload, ImagePayload]):
        def __init__(self,
                     model: str,
                     device: str,
                     confidence: float,
                     **kwargs):
            super().__init__(**kwargs)

            self.model_name = model
            self.device = device
            self.confidence = confidence
            self.model = None

Our node does not need much. It only instantiates a YOLO model, and that can be
done in the ``warmup`` method:

.. code-block:: python

    def warmup(self):
        self.model = YOLO(self.model_name)
        self.model.to(self.device)

        self.logger.info('model properly loaded')

The processing logic of the node is pretty simple, and should all be contained
in the ``update`` method. Every image the node receives needs to go through the
model, annotated, and sent upstream to all the listening destinations. Code-wise
this looks like this:

.. code-block:: python

    def update(self, message: Message[ImagePayload]):
        image = message.payload.image
        results = self.model.predict(
            image,
            verbose=False,
            conf=self.confidence,
        )

        annotated = results[0].plot()

        to_send = Message[ImagePayload](
            creator=self.name,
            version=message.version,
            payload=ImagePayload(
                image=annotated,
                width=annotated.shape[1],
                height=annotated.shape[0],
                depth=annotated.shape[2],
                pixel_format=message.payload.pixel_format,
                timestamp=message.payload.timestamp,
            ),
            timers_from=message,
        )

        to_send.meta['annotations'] = results[0]

        self.transmit(to_send)

Logging
-------

The ``Node`` class comes shipped with a logger object that all nodes can use. A
node logger is a child of the root logger, and will be named
``jt.<PIPE_NAME>.<NODE_NAME>``. To use it, simply run:

.. code-block:: python

    self.logger.info('node-specific logging entry')