Remotise a node
===============

This guide demonstrates how to convert a local node into a remote node using the
``Warp`` node feature.

Starting point: local pipeline
------------------------------

Consider a simple pipe with three nodes:

- a ``data_streamer`` source that generates data
- a ``passthrough_identity`` processing node that introduces a 2-second delay
- a ``notifier_websocket`` sink that sends results to a WebSocket endpoint

This pipeline can be implemented through a simple local configuration file.

.. code-block:: json

    {
      "version": "0.1.0",
      "plugins": ["./plugins"],
      "pipeline": {
        "name": "test_mocked_pipeline",
        "id": "1234567890",
        "folder": "./pipe",
        "nodes": [
          {
            "name": "0_stream",
            "type": "source",
            "mark": "data_streamer",
            "configuration": {}
          },
          {
            "name": "1_pass",
            "type": "proc",
            "mark": "passthrough_identity",
            "configuration": {
              "delay": 2
            }
          },
          {
            "name": "2_notifier",
            "type": "sink",
            "mark": "notifier_websocket",
            "configuration": {
              "endpoint": "ws://127.0.0.1:8081"
            }
          }
        ],
        "links": [
          {
            "from": "0_stream",
            "to": "1_pass"
          },
          {
            "from": "1_pass",
            "to": "2_notifier"
          }
        ]
      }
    }

In our scenario, we want to deploy the ``passthrough_identity`` node remotely.
Of course, it doesn't make much sense to remotise this specific node, however,
the same concepts apply for nodes that might require resources not available
locally (GPU-dependent nodes are a great example).

Remotising a node is just as simple as specifying the connection coordinates in
its configuration, and adding a flag. The node configuration object then
becomes:

.. code-block:: json

    {
      "name": "1_pass",
      "type": "proc",
      "mark": "passthrough_identity",
      "configuration": {
        "delay": 2
      },
      "warped": true,
      "warp_configuration": {
        "grpc_host": "172.17.0.1",
        "grpc_port": 45000,
        "timeout": 5
      }
    }

In the ``warp_configuration`` object, we added:

- ``grpc_host``, the ip address of the remote service where the concrete node is
  hosted
- ``grpc_port``, the port number where the remote service is listening
- ``timeout``, how long is the warp node supposed to wait for an answer from the
  remote service

Start the remote service
------------------------

Once everything is in place on the local side, we need to start the remotisation
service on the remote side, that is, launch juturna so that the node to make
remote is instantiated and made available behind a service. To do so, we need to
install juturna on the remote side making sure to:

- include the ``warp`` group in the installation
- have the remotised node available in the ``./plugin`` folder

Assuming you already copied the plugins in the remote location, we can proceed:

.. code-block:: bash

    remote:~/prj$ pip install "juturna[warp]"
    remote:~/prj$ python -m juturna remotize \
        --node-name "1_pass" \
        --plugins-dir "./plugins" \
        --pipe-name "test_mocked_pipeline" \
        --node-mark "passthrough_identity" \
        --default-config '{"delay": 2}' \
        --port 45000
