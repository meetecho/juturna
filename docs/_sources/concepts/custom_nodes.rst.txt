#################
Node fundamentals
#################

A node is a class that extends ``juturna.components.BaseNode``. When
implementing a custom node, respect the following structure::

  ./plugins
    └── nodes
        └── <NODE_TYPE>
            └── _<NODE_NAME>
                ├── <NODE_NAME>.py
                ├── config.toml
                ├── requirements.txt
                └── readme.md

Notes:

- you can pick ``<NODE_TYPE>`` to be anything you want (the built-in nodes are
  split into ``source``, ``proc``, and ``sink``, so it could be a good idea to
  stick with those)
- make sure the node folder name starts with an underscore (``_``)
- make sure the node file has the same name of its parent folder, but without
  the underscore
- a ``readme.md`` file is not required, but higly recommended
- Juturna does not take care (for now!) of individual node requirements, so
  make sure you install all the required packages using the
  ``requirements.txt`` included in each external node you use

Node configuration
==================

The configuration file of a node is a ``toml`` file with only 2 fields:

- ``[arguments]`` contains the arguments that will be provided to the node
  constructor
- ``[meta]`` reserved, you can leave this empty

::

   [arguments]
   param_1 = 10
   param_2 = "string_value"

Node class
==========

In the following, an example will be provided for a node called ``CustomNode``
within the ``custom_node.py`` file. This node will receive as arguments the
ones showed earlier.

::

   from juturna.components import BaseNode
   from juturna.components import Message

   from juturna.payloads import BytesPayload, AudioPayload


   class CustomNode(BaseNode[BytesPayload, AudioPayload]):
       def __init__(self, param_1: int, param_2: str, **kwargs):
           super().__init__(**kwargs)

       def update(self, message: Message[BasicPayload]):
           ...

The node class signature reports the types of input and output payloads the
node respectively expects as input and produces as output. Additionally, a set
of arguments will be automatically added when the node is first instantiated,
under ``kwargs``. This contains:

- ``node_name``, the name assigned to the node,
- ``node_type``, the node type specified in the configuration file,
- ``pipe_name``, the name of the pipe where the node was created.

Notes:

- do not include other keyword arguments in the node constructor: the argument
  values stored in the configuration file will be treated as default values for
  the node, whenever not provided in the pipeline configuration

+------------------------+---------------------+-----------------------------+
| property               | type                | description                 |
+========================+=====================+=============================+
| ``self.configuration`` | ``dict``            | node name and id            |
+------------------------+---------------------+-----------------------------+
| ``self.name``          | ``str``             | node name                   |
+------------------------+---------------------+-----------------------------+
| ``self.pipe_id``       | ``str``             | unique identifier for the   |
|                        |                     | pipeline containing the node|
+------------------------+---------------------+-----------------------------+
| ``self.status``        | ``ComponentStatus`` | node status                 |
+------------------------+---------------------+-----------------------------+
| ``self.pipe_path``     | ``str``             | absolute path of the folder |
|                        |                     | assigned to the node within |
|                        |                     | the pipeline folder         |
+------------------------+---------------------+-----------------------------+
| ``self.static_path``   | ``str``             | absolute path of the folder |
|                        |                     | where the node files reside |
|                        |                     | (used to fetch static       |
|                        |                     | resources)                  |
+------------------------+---------------------+-----------------------------+
| ``self.logger``        | ``logging.Logger``  | internal node logger (this  |
|                        |                     | will have the same name as  |
|                        |                     | the node)                   |
+------------------------+---------------------+-----------------------------+

+-----------------------------+-----------------------+-----------------------------+
| method                      | arguments             | description                 |
+=============================+=======================+=============================+
| ``self.configure()``        | ``()``                | configure the node (request |
|                             |                       | resources and perform other |
|                             |                       | system-dependent            |
|                             |                       | intialisations)             |
+-----------------------------+-----------------------+-----------------------------+
| ``self.warmup()``           | ``()``                | implement node warmup       |
|                             |                       | operations                  |
+-----------------------------+-----------------------+-----------------------------+
| ``self.set_source()``       | ``(callable)``        | set the data source for the |
|                             |                       | node (to be called only for |
|                             |                       | source nodes)               |
+-----------------------------+-----------------------+-----------------------------+
| ``self.prepare_template()`` | ``(str, str, dict)``  | compile a template file     |
|                             |                       | in the node folder and      |
|                             |                       | save it in the pipeline     |
|                             |                       | folder                      |
+-----------------------------+-----------------------+-----------------------------+
| ``self.start()``            | ``()``                | start the node bridge       |
+-----------------------------+-----------------------+-----------------------------+
| ``self.stop()``             | ``()``                | stop the node bridge        |
+-----------------------------+-----------------------+-----------------------------+
| ``self.set_on_config()``    | ``(str, typing.Any)`` | update node property while  |
|                             |                       | the node is running         |
+-----------------------------+-----------------------+-----------------------------+
| ``self.update()``           | ``(Message)``         | receive and process the     |
|                             |                       | latest message from source  |
+-----------------------------+-----------------------+-----------------------------+
| ``self.transmit()``         | ``(Message)``         | send a message forward in   |
|                             |                       | the pipeline                |
+-----------------------------+-----------------------+-----------------------------+

Notes:

- the ``set_source()`` method should contain a function that is periodically
  invoked by the node, but setting a source is only required for source nodes,
  as the function specified as source is blocking for the node
- if a node needs to perform particular operations during ``start`` and
  ``stop``, then use ``super().start()`` and ``super().stop()`` respectively to
  make sure the corresponding methods in the base class are properly invoked
- ``configure``, ``warmup``, ``start``, ``stop`` and ``destroy`` are not
  required when implementing a node; you should add them to your node only if
  you need them
- the ``update()`` method always has an object of type ``Message`` as argument,
  and it is automatically invoked whenever the source node (that is, the node
  this current node is connected to) produces a new piece of data; when
  implementing the update method for your node, check how the content of the
  message you receive is arranged by the source node
- the ``transmit()`` method should ideally be invoked within the ``update()``
  method; always remember to update the version of the data you are sending,
  otherwise no ``update()`` will be triggered in the destination node
- the ``set_on_config()`` method should be invoked through the pipeline that
  holds the node. When you design a custom node, make sure this method contains
  all the essential checks before updating a configuration item.
- a node needs to exist within a pipeline so that templates can be compiled and
  saved (if the node does not belong to a pipeline, then its ``pipe_path`` will
  not be specified, hence the compiled template will have no destination
  folder); at any rate, a ``pipe_path`` should be defined for the node

Node payloads
=============
A node class specifies the types the node expects as input, and offers as
output. Specifying the payloads in the node signature helps users understanding
what sort of data the node produces.

For a node signature like this::

  class NodeName(BaseNode[AudioPayload, ObjectPayload]):
      ...

we are defining a node that expects audio data as input, and transmits object to
all the nodes attached to it. The relevance of the payload specification is also
shown in the ``update`` method::

  def update(self, message: AudioPayload):
      data = message.payload.waveform
      to_send = Message(payload=ObjectPayload())
      ...
      self.transmit(to_send)

For an overview of what built-in payloads look like, take a look at the
:doc:`paylaod doc page <./payloads>`.

Logging
=======
The ``BaseNode`` class comes shipped with a logger object that all nodes can
use. A node logger is a child of the root logger, and will be named
``jt.<PIPE_NAME>.<NODE_NAME>``. To use it, simply run::

  def update(self, message: AudioPayload):
      self.logger.info('node-specific logging entry')

Node templates
==============

A node can carry template files, so that they can be dynamically compiled when
needed and stored in the node pipeline folder. The ``prepare_template()`` node
method can be used to do so. Assuming a node contains the following files::

    ./plugins
    └── nodes
        └── <NODE_TYPE>
            └── _<NODE_NAME>
                ├── <NODE_NAME>.py
                ├── config.toml
                ├── requirements.txt
                ├── content.json.template
                └── readme.md

In this case, ``content.json.template`` is a simple template file where a number
of fields are defined::

  # content of the template file
  { "arg_1": "$param_1", "arg_2": "$param_2" }

Then within the node code, the template file can be compiled and saved as
follows::

  ...
  
  self.prepare_template(
      'content.json.template',
      'content.json',
      { 'param_1': 'value_1', 'param_2': 'value_2' })
  
  ...

This will result in a file called ``content.json`` to be created in the node
pipeline folder, ready to be used by the node::

  # compiled template stored in the node pipeline folder
  { "arg_1": "value_1", "arg_2": "value_2" }

Full node example
-----------------

This is an example of a node that receives an audio message and produces a
image message.

::

   from juturna.components import BaseNode
   from juturna.components import Message

   from juturna.payloads._payloads import AudioPayload, ImagePayload


   class CustomNode(BaseNode[AudioPayload, ImagePayload]):
       def __init__(self, param_1: int, param_2: str, **kwargs):
           super().__init__(**kwargs**)

           self._param_1 = param_1
           self._param_2 = param_2

           self.logger.info('node created')

       def configure(self):
           # acquire system resources such as network ports, devices, or
           # filesystem entities
           # if this is a source node, you can invoke the set_source function
           # here
           ...

       def set_on_config(self, property: str, value: Any):
           # update a node property while the node is in execution
           ...

       def warmup(self):
           # perform warmup operations
           # if this is a source node, you can invoke the set_source function
           # here
           ...

       def start(self):
           # perform operations required when node starts
           # if this method is implemented here, remember to call the parent
           # start() method
           ...
           super().start()

       def stop(self):
           # perform operations required when node stops
           # if this method is implemented here, remember to call the parent
           # stop() method
           ...
           super().stop()

       def destroy(self):
           # perform cleanup operations for the node, if needed
           ...

       def update(self, message: Message[AudioPayload]):
           # receive data from the source node, process them, and generate
           # new data for the destination node
           data = message.payload.waveform
           current_version = message.version

           new_data = do_stuff(data)

           new_message = Message[ImagePayload](
            creator=self.name,
            payload=ImagePayload(image=new_data))
           new_message.version = current_version + 1

           self.transmit(new_message)
