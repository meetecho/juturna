############
Juturna APIs
############


.. toctree::
   :maxdepth: 2
   :glob:
   :caption: APIs
   
   ../apis/juturna

.. ``juturna.components``
.. ======================

.. ``juturna.components.BaseNode``
.. -------------------------------

.. .. autoclass:: juturna.components.BaseNode
..    :private-members: __init__

.. Properties
.. ----------

.. ..   autoproperty:: juturna.components.BaseNode.name
.. ..   autoproperty:: juturna.components.BaseNode.status
.. ..   autoproperty:: juturna.components.BaseNode.pipe_id
.. ..   autoproperty:: juturna.components.BaseNode.pipe_path
.. ..   autoproperty:: juturna.components.BaseNode.static_path

.. Methods
.. -------

.. .. automethod:: juturna.components.BaseNode.set_source
.. .. automethod:: juturna.components.BaseNode.transmit
.. .. automethod:: juturna.components.BaseNode.start
.. .. automethod:: juturna.components.BaseNode.stop

.. ------------

.. ``juturna.components.Pipeline``
.. -------------------------------

.. Constructor
.. -----------

.. .. autoclass:: juturna.components.Pipeline
..    :private-members: __init__

.. Properties
.. ----------
.. .. autoproperty:: juturna.components.Pipeline.pipe_id
.. .. autoproperty:: juturna.components.Pipeline.pipe_folder
.. .. autoproperty:: juturna.components.Pipeline.name
.. .. autoproperty:: juturna.components.Pipeline.status

.. Methods
.. -------
.. .. automethod:: juturna.components.Pipeline.from_json
.. .. automethod:: juturna.components.Pipeline.warmup
.. .. automethod:: juturna.components.Pipeline.start
.. .. automethod:: juturna.components.Pipeline.stop
.. .. automethod:: juturna.components.Pipeline.destroy

.. ------------

.. ``juturna.components.Message``
.. -----------------------------

.. Constructor
.. -----------
.. .. autoclass:: juturna.components.Message
..    :private-members: __init__

.. Properties
.. ----------
.. .. autoproperty:: juturna.components.Message.creator
.. .. autoproperty:: juturna.components.Message.version
.. .. autoproperty:: juturna.components.Message.payload
.. .. autoproperty:: juturna.components.Message.meta
.. .. autoproperty:: juturna.components.Message.timers

.. Methods
.. -------
.. .. automethod:: juturna.components.Message.from_message
.. .. automethod:: juturna.components.Message.to_dict
.. .. automethod:: juturna.components.Message.to_json
.. .. automethod:: juturna.components.Message.timer
.. .. automethod:: juturna.components.Message.timeit

.. ``juturna.utils``
.. =================

.. Juturna utils is a collection of utility functions that can be used perform a
.. number of tasks.

.. .. automethod:: juturna.utils.node_utils.node_stub

.. ``juturna.hub``
.. ===============