Run pipelines behind an HTTP service
====================================

``juturna serve`` starts a service that creates and manages pipelines for its
clients, over HTTP. Use it when pipelines are launched by another program (a
web interface, a scheduler) rather than by hand.

This guide starts the service and drives a pipeline through its whole life
with ``curl``. The full list of requests is in :ref:`reference_http_api`.

Start the service
-----------------

The service needs the ``httpwrapper`` group:

.. code-block:: console

    (.venv) $ pip install 'juturna[httpwrapper]'

Every request must carry a token. Choose one and pass it in the
``JUTURNA_SERVICE_TOKEN`` environment variable, then start the service with a
port and the folder where the pipelines will keep their files:

.. code-block:: console

    (.venv) $ export JUTURNA_SERVICE_TOKEN="choose-a-long-random-string"
    (.venv) $ python -m juturna serve --port 8000 --folder ./pipelines

If the variable is not set, the service makes a random token and prints it
when it starts.

The node packages your pipelines use must be installed in the same
environment as the service.

Create and start a pipeline
---------------------------

Send a pipeline configuration (the same JSON file used by ``juturna launch``)
to ``/pipelines/deploy``. The service creates the pipeline, warms it up and
starts it:

.. code-block:: console

    $ curl -H "Authorization: Bearer $JUTURNA_SERVICE_TOKEN" \
           -H 'Content-Type: application/json' \
           -d @pipeline.json \
           localhost:8000/pipelines/deploy

The answer is the status of the pipeline. Take note of its ``pipe_id``: the
service gives every pipeline a new id and a folder of its own, whatever the
``id`` and ``folder`` of the configuration say.

To go one step at a time, use ``/pipelines/new`` (the id is in
``data.pipeline_id`` of the answer), then ``/pipelines/<id>/warmup`` and
``/pipelines/<id>/start``.

Look at it
----------

.. code-block:: console

    $ curl -H "Authorization: Bearer $JUTURNA_SERVICE_TOKEN" \
           localhost:8000/pipelines/<id>/status

The status includes the state of every node and its ``health``: how many
times it failed, and its most recent error. ``/pipelines/<id>/logs`` returns
the latest log records, ``/pipelines/<id>/files`` the files the pipeline wrote.

Stop and remove it
------------------

.. code-block:: console

    $ curl -X POST -H "Authorization: Bearer $JUTURNA_SERVICE_TOKEN" \
           localhost:8000/pipelines/<id>/stop
    $ curl -X POST -H "Authorization: Bearer $JUTURNA_SERVICE_TOKEN" \
           'localhost:8000/pipelines/<id>/delete?wipe=true'

``wipe=true`` also removes the folder of the pipeline. A stopped pipeline
cannot be started again: delete it and deploy a new one.

Let configurations read environment variables
---------------------------------------------

Clients cannot read the environment of the service through ``$JT_ENV_``
values, unless you allow the variables one by one:

.. code-block:: console

    (.venv) $ python -m juturna serve -p 8000 -f ./pipelines --allow-env AUTH_TOKEN

See :doc:`environment`.

Get the logs you need
---------------------

Without further settings the service keeps warnings and errors only. To
change that, pass a logging configuration, a JSON file in the format of
Python's ``logging.config.dictConfig``:

.. code-block:: json

    {
      "version": 1,
      "disable_existing_loggers": false,
      "loggers": {
        "jt": { "level": "INFO" }
      }
    }

.. code-block:: console

    (.venv) $ python -m juturna serve -p 8000 -f ./pipelines --log-config logging.json

Expose it safely
----------------

The service listens on ``127.0.0.1`` by default, so only programs on the same
machine reach it. Before passing another address with ``--host``, consider
that:

- the service speaks plain HTTP, so the token travels in clear: put it behind
  a proxy that adds TLS;
- whoever has the token can run any installed node with any configuration on
  your machine. Give it only to clients you trust;
- ``--no-auth`` turns the token check off. Use it only for development, or
  behind a layer that authenticates the clients;
- ``--dev`` allows requests from web pages of other origins, which a browser
  application under development needs. Leave it off otherwise.
