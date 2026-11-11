Run a node on another machine
=============================

A node that needs resources your machine does not have (a GPU, a large
model) can run somewhere else and still be part of your pipeline. Juturna
calls this *warping* the node. This guide moves one node of a pipeline to a
remote service; :ref:`explain_remote` explains how it works.

We start from a pipeline with three nodes:

.. code-block:: json

    {
      "version": "3.0.0",
      "pipeline": {
        "name": "my_pipeline",
        "id": "my_pipeline_01",
        "folder": "./run",
        "nodes": [
          {
            "name": "receiver",
            "type": "JsonHTTP",
            "configuration": {}
          },
          {
            "name": "delay",
            "type": "PassthroughIdentity",
            "configuration": { "delay": 2 }
          },
          {
            "name": "notifier",
            "type": "NotifierHTTP",
            "configuration": { "endpoint": "http://127.0.0.1:8081" }
          }
        ],
        "links": [
          { "from": "receiver", "to": "delay" },
          { "from": "delay", "to": "notifier" }
        ]
      }
    }

We want ``delay`` to run on another machine. It makes little sense for this
node, but the steps are the same for one that needs a GPU.

Start the remote service
------------------------

On the remote machine, install Juturna with the ``warp`` group, and the
package that contains the node:

.. code-block:: console

    remote $ pip install 'juturna[warp]' juturna-nodes

The remote node is configured once, when the service starts, from a JSON file
with its arguments. Save this as ``delay.json``:

.. code-block:: json

    { "delay": 2 }

Then start the service:

.. code-block:: console

    remote $ python -m juturna remotize \
                    --node-name delay \
                    --node-type PassthroughIdentity \
                    --default-config delay.json \
                    --host 0.0.0.0 \
                    --port 50051

.. warning::

    The remote service has no authentication and no encryption, so it listens
    on ``127.0.0.1`` unless told otherwise. ``--host 0.0.0.0`` makes it
    reachable from other machines: use it **on trusted networks only**, or
    behind a tunnel or a proxy that authenticates and encrypts.

Warp the node in the pipeline
-----------------------------

On the local machine, the pipeline needs the ``Warp`` node, which comes with
``juturna-nodes``:

.. code-block:: console

    local $ pip install 'juturna-nodes[warp]'

In the pipeline configuration, mark the node as warped and tell where the
remote service is:

.. code-block:: json

    {
      "name": "delay",
      "type": "PassthroughIdentity",
      "configuration": { "delay": 2 },
      "warped": true,
      "warp_configuration": {
        "grpc_host": "192.168.1.20",
        "grpc_port": 50051,
        "timeout": 5
      }
    }

- ``grpc_host`` and ``grpc_port`` are the address of the remote service;
- ``timeout`` is how many seconds the pipeline waits for each answer.

The ``configuration`` of a warped node is not applied: the remote service
uses its own, and logs a warning to say so.

Launch the pipeline as usual. Messages for ``delay`` now go to the remote
service, and its answers continue down the pipeline.

Both sides must run matching versions of Juturna. When they do not, the first
message fails with an error that says so.

Put several replicas behind a load balancer
-------------------------------------------

By default a warped node is **sticky**: the remote service keeps the state of
the node between messages, so the pipeline must always reach the same service.

To spread the work over several replicas, add ``"sticky": false`` next to
``"warped": true``, and point ``grpc_host`` to the load balancer. The state
then travels with every request, so any replica can serve it. Keep the state
small, and made of plain values, numpy arrays and messages.

Write nodes that can be warped
------------------------------

A node works remotely when it follows two rules:

- it transmits from ``update()`` only, and at most one message per call;
- what it puts in messages and in its state can travel: plain values, numpy
  arrays, messages. No open files, no models.

Start the service with ``--strict`` while testing: instead of silently
leaving out what cannot travel, it fails the request.
