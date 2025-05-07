################
Common questions
################

Pipeline execution
==================

.. dropdown:: Messages fail to propagate

   Q: The first message from the source is the only one that propagates in the
   pipeline, any subsequent message is ignored. Why?

   A: This often happens because the source node that generates the data
   messages does not set the version in the messages it sends. As a result, the
   very first message will trigger a version change from ``-1`` (the default
   data version recorded in an empty buffer) to ``None`` (the default message
   version set in an empty message). This version change will be detected by
   all the node waiting for updates on that buffer, but any following messages
   will have their version set to ``None``, so nothing will be triggered.

   As a general rule, when designing a node, always treat the version of any
   sent messages as a counter of how many messages that node produced. This can
   be done with a counter local to the node, or by updating the version of the
   received message::

     def update(self, message: Message):
         received_version = message.version

         # an empty message has its version set to None
         message_to_send = Message(creator=self.name)

         ...

         # option 1: use the received version and increment it
         message_to_send.version = received_version + 1

         # option 2: count the number of sent messages locally
         message_to_send.version = self._local_counter
         self._local_counter += 1

         self.transmit(message_to_send)

.. dropdown:: Plugin nodes are not loaded

   Q: I want to use a plugin node that requires the import of an extra module
   from within the node folder itself, but it does not work. Why?

   A: By design, the location of a node also dictates where the node class can
   look for extra local modules to import. To give you an example, If a node
   class ``MyAwesomeNode`` wants to use a separate module called
   ``my_awesome_utils``, it will need to know the path where that module can be
   imported. So, assuming the node code lives in the folder
   ``./plugins/nodes/proc/my_awesome_node``, then the node will do something
   like this to import the extra::

     from plugins.nodes.proc.my_awesome_node import my_awesome_utils

   Because of this reason, all plugin nodes downloadable from the Juturna
   repository are expected to be placed in a folder ``./plugin`` within your
   project folder.
