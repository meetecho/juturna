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


   class CustomNode(BaseNode):
       def __init__(self, param_1: int, param_2: str):
           super().__init__('proc')

       def update(self, message: Message):
           ...

Notes:

- do not include keyword arguments in the node constructor: the argument values
  stored in the configuration file will be treated as default values for the
  node, whenever not provided in the pipeline configuration

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

+-----------------------------+----------------------+-----------------------------+
| method                      | arguments            | description                 |
+=============================+======================+=============================+
| ``self.configure()``        | ``()``               | configure the node (request |
|                             |                      | resources and perform other |
|                             |                      | system-dependent            |
|                             |                      | intialisations)             |
+-----------------------------+----------------------+-----------------------------+
| ``self.warmup()``           | ``()``               | implement node warmup       |
|                             |                      | operations                  |
+-----------------------------+----------------------+-----------------------------+
| ``self.set_source()``       | ``(callable)``       | set the data source for the |
|                             |                      | node (to be called only for |
|                             |                      | source nodes)               |
+-----------------------------+----------------------+-----------------------------+
| ``self.prepare_template()`` | ``(str, str, dict)`` | compile a template file     |
|                             |                      | in the node folder and      |
|                             |                      | save it in the pipeline     |
|                             |                      | folder                      |
+-----------------------------+----------------------+-----------------------------+
| ``self.start()``            | ``()``               | start the node bridge       |
+-----------------------------+----------------------+-----------------------------+
| ``self.stop()``             | ``()``               | stop the node bridge        |
+-----------------------------+----------------------+-----------------------------+
| ``self.update()``           | ``(Message)``        | receive and process the     |
|                             |                      | latest message from source  |
+-----------------------------+----------------------+-----------------------------+
| ``self.transmit()``         | ``(Message)``        | send a message forward in   |
|                             |                      | the pipeline                |
+-----------------------------+----------------------+-----------------------------+

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
- a node needs to exist within a pipeline so that templates can be compiled and
  saved (if the node does not belong to a pipeline, then its ``pipe_path`` will
  not be specified, hence the compiled template will have no destination
  folder); at any rate, a ``pipe_path`` should be defined for the node

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

::

   from juturna.components import BaseNode
   from juturna.components import Message


   class CustomNode(BaseNode):
       def __init__(self, param_1: int, param_2: str):
           super().__init__('proc')

           self._param_1 = param_1
           self._param_2 = param_2

       def configure(self):
           # acquire system resources such as network ports, devices, or
           # filesystem entities
           # if this is a source node, you can invoke the set_source function
           # here
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

       def update(self, message: Message):
           # receive data from the source node, process them, and generate
           # new data for the destination node
           data = message.payload
           current_version = message.version

           new_data = do_stuff(data)

           new_message = Message(creator=self.name)
           new_message.version = current_version + 1

           self.transmit(new_message)
