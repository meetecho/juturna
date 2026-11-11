.. _explain_remote:

Remote components
=================

When creating a juturna pipeline, all its components are instantiated locally.
Whilst this is ideal when developing new nodes and checking that everything
works fine on your own machine or container, in many production scenarios having
the ability to leverage remote resources, such as GPUs, is not a plus but a
must. For this reason, juturna offers the basic infrastructure to deploy nodes
remotely, while still using them as if they were local entities. We call this
**warping**.

Warping a node enables the remote execution of that node, included in a local
pipe. You can deploy specific nodes as remote services that communicate with the
main pipe over the network using gRPC and Protocol Buffers (Google's
`protobuf <https://github.com/protocolbuffers/protobuf>`_).

This architecture allows a local pipe to offload processing to remote node
handlers, which manage the node lifecycle and act as message brokers for
incoming and outgoing queues.

The warping mechanism addresses common topics in several deployment scenarios.
To name a few, remote nodes are deployed with dependency isolation, so they do
not clash with conflicting dependencies from other nodes in the same pipeline.
Also, sharing and scaling are strong suits of remote nodes, as they can serve
multiple pipelines simultaneously, or be made redundant and masked by a load
balancer.

.. admonition:: Remotisation is young
    :class: :WARNING:

    The infrastructure to deploy juturna nodes remotely is still under
    active development. The remote service has no authentication and no
    encryption (see `Who can reach the service`_), so it is meant for trusted
    networks only.

Warping fundamentals
--------------------

When a node is configured for remote execution, two components work together. On
the local side (that is, the `main` juturna process) a node intended for remote
deployment is masked by a **warp node**. A warp node is a simple processing node
acting as local client or proxy for the remote node. Warp nodes are responsible
for managing the communication with the remote service behind which the concrete
node lives. This means, they receive messages from the pipeline normally, turn
them into protocol buffers, send them over the remote service, and then unpack
the responses they receive.

On the remote side runs the **remote service**, a standalone gRPC server that
holds the concrete node doing the actual computation work, acting as a
publish/subscribe broker for its input and output queues. Similarly to the warp
node, the remote service manages the marshalling and unmarshalling of the data
received from the local pipe.

.. image:: ../_static/img/remote_structure.svg
   :alt: remote juturna
   :width: 80%
   :align: center

State and replicas
------------------

The concrete node keeps its state between messages, like a local one. Each warp
node gets its own state on the remote side, even when one remote service serves
several pipelines, and the ``sticky`` flag of the warped node tells where that
state lives:

- **sticky** (the default): the remote service keeps the state of each warp
  node, and sends a copy back with every response. The warp node must always
  reach the same service. It sends its copy only when the service answers that
  it does not know it, after a restart or once an idle state was dropped, and
  the service starts again from that copy.
- **not sticky**: the remote service keeps nothing. The warp node sends its
  state with every request, the remote node updates it, and the response brings
  it back. Any replica behind a load balancer can serve any request, and a
  replica going down loses no state. The state travels on every request, so
  keep it small.

A warp node makes a random **session** identifier every time it warms up, and
sends it with every request. The service keeps a sticky state under the
pipeline id, the name of the warp node and that session. So another client
that only knows the pipeline id and the node name gets a state of its own,
and a pipeline that is started again does not continue from the state of its
previous run: it is asked for its copy, like any client the service does not
know. When a sticky warp node is destroyed it tells the service, which drops
its state at once.

In both cases the remote service answers when ``update()`` returns. A message
that the node keeps in its state without transmitting anything gets an empty
response at once, and the warp node transmits nothing downstream.

What cannot reach the client
----------------------------

Messages and states keep their exact types on the wire: ``None``, booleans,
ints, floats, strings, bytes, lists, tuples, frozensets, dictionaries, numpy
arrays and scalars, and messages. Some things still cannot reach the warp node:

- a value of another type (a set, an open file, a model) in the ``meta`` of a
  message, in an ``ObjectPayload`` or in the state, as well as an integer
  outside the 64-bit range and a string that is not valid Unicode;
- a second message transmitted by the same ``update()``: only the first one is
  sent back;
- a message transmitted after ``update()`` returned, or by a thread of the
  node other than the one running ``update()``: it never answers a request,
  since the request being processed at that moment may belong to another
  pipeline.

By default the remote service leaves them out and logs a warning, once for
each client and for each kind of loss: a dictionary loses the entry, a list or
a tuple the item, and everything else is sent. A state that loses an entry
loses it for good, in the copy kept by a sticky warp node as well, so keep
such objects in the node rather than in its state. The warp node does the same
with the messages it sends.

Started with ``--strict``, the remote service fails the request with the
``DATA_LOSS`` gRPC status instead, every time. A message transmitted late fails
the next request of its warp node, which is not processed. The warp node
counts the failure in its health, and the pipeline goes on with the next
message.

The remote service can only tell which warp node a late message was meant for
while the node is idle. A message transmitted by another thread while the node
processes a message is logged as an error instead, in both modes, and fails no
request. A node meant to run remotely transmits from ``update()`` only.

Who can reach the service
-------------------------

The remote service has **no authentication and no encryption**. Whoever can
connect to it can send messages to the node and read what comes back, and
whoever can read the traffic sees everything, sessions included. The session
keeps well-behaved clients apart; it is not a password.

For this reason ``juturna remotize`` listens on ``127.0.0.1`` by default,
reachable from the same machine only. To serve pipelines on other machines,
pass the address to listen on with ``--host`` (``0.0.0.0`` for every
interface), and do it **on trusted networks only**: a private network between
your own machines, or behind a proxy or a tunnel that authenticates and
encrypts. The service logs a warning when it listens on anything but the
loopback address.

Protocol version
----------------

The warp node and the remote service must speak the same version of the remote
protocol, which is version 1 in juturna 3.0. Every request and response carries
it. The service refuses a request of another version with the
``UNIMPLEMENTED`` status, and the warp node refuses a response of another
version, so two sides that do not match fail on the first message with an
error that says so. A message whose payload is of a type the receiver does not
know is refused too, on both sides.

The version changes whenever an older peer would not understand the new one.
Install matching versions of juturna on both sides: on the local side that is
the version ``juturna-nodes`` was installed with.

Limits
------

The remote service keeps the state of at most ``--max-clients`` sticky warp
nodes (1024 by default) and refuses new ones with the ``RESOURCE_EXHAUSTED``
status, until a state is dropped after an hour without requests. It accepts
``--max-requests`` requests at once (10 for each worker by default), in
progress or waiting for a worker, and refuses the others with the same
status. A request whose warp node cancels it or disconnects is not processed
if it is still waiting.

``juturna remotize`` exits with status 1 when the node cannot be built or the
address is already in use: two services never share a port.

Developer notes
---------------

Juturna installation includes pre-compiled protobuf classes, ready to use out of
the box. However, if you need to modify the .proto definitions or recompile them
for development purposes, two utility scripts are provided:

- ``juturna/remotizer/compile_protos.sh``: Recompiles the .proto files into
  Python classes
- ``juturna/remotizer/expose_protos.sh``: Exports the compiled protobuf classes
  for external use. This requires to install the additional ``protoletariat``
  dependency.

These scripts should only be needed when modifying the protocol definitions or
contributing to the Warp node implementation.
