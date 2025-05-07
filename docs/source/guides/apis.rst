############
Juturna APIs
############

Components
==========

This package contains the basic entities to be used when creating pipelines and
nodes. Namely, those are:

- ``BaseNode``: the node base class to be used when creating a custom node
- ``Pipeline``: the pipeline container
- ``Message``: the data container to be passed across a pipeline nodes

``juturna.components.BaseNode``
-------------------------------

.. autoclass:: juturna.components.BaseNode
   :private-members: __init__

.. autoproperty:: juturna.components.BaseNode.name


``juturna.components.Pipeline``
-------------------------------

.. autoclass:: juturna.components.Pipeline

Names
=====

Juturna names are static values that are used to share statuses across
different components.

.. autoclass:: juturna.names.ComponentStatus

Meta
========

This package contains environment variables useful to configure the hub.

Hub
=======

This package contains the utility functions that can be used to download remote
plugins.

.. autofunction:: juturna.hub.list_plugins

.. autofunction:: juturna.hub.download_node

.. autofunction:: juturna.hub.download_pipeline
