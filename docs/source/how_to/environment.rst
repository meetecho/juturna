Use environment variables in a configuration
============================================

Some values do not belong in a configuration file: a token, a password, a
path that changes from machine to machine. This guide shows how to read them
from the environment, and how to limit what a configuration can read.

(Looking for the variables that tune Juturna itself? See
:ref:`reference_constants`.)

Read a variable
---------------

Take a sink node that needs a secret token:

.. code-block:: json

    {
      "name": "destination",
      "type": "contrib.acme.nodes.AuthenticatedSink",
      "configuration": {
        "endpoint": "127.0.0.1",
        "secret_token": "plain_token_is_dangerous!"
      }
    }

To take the token from a variable called ``AUTH_TOKEN``, write its name with
the ``$JT_ENV_`` prefix:

.. code-block:: json

    {
      "name": "destination",
      "type": "contrib.acme.nodes.AuthenticatedSink",
      "configuration": {
        "endpoint": "127.0.0.1",
        "secret_token": "$JT_ENV_AUTH_TOKEN"
      }
    }

Then set the variable before launching the pipeline:

.. code-block:: console

    $ export AUTH_TOKEN="s3cr3t"
    $ python -m juturna launch --config pipeline.json

The value is converted to the type of the default the node declares for that
argument in its ``config.toml``: a variable for an integer argument must hold
an integer. For a boolean argument, ``true``, ``1`` and ``yes`` (in any case)
mean true, anything else means false.

A variable that is not set makes the warm up fail with an error naming it.
``juturna validate`` only warns, as the variable may be set where the pipeline
will run.

Limit what a configuration can read
-----------------------------------

A pipeline you build yourself, or launch with ``juturna launch``, can read any
variable of the environment. This is not what you want when the configuration
comes from somebody else, who could point a node at any secret of your
process.

The pipeline service (``juturna serve``) reads no variable by default: a
configuration that references one is refused with ``403``. Name the variables
its clients can use with ``--allow-env``, once per variable:

.. code-block:: console

    $ python -m juturna serve -p 8000 -f ./pipelines \
             --allow-env AUTH_TOKEN --allow-env MODEL_DIR

The list covers both the ``configuration`` and the ``warp_configuration`` of a
node.

The same list is available when you build pipelines in your own code from
configurations you do not control:

.. code-block:: python

    pipeline = jt.components.Pipeline(config, allowed_env_vars=['AUTH_TOKEN'])

A configuration that reads any other variable raises ``EnvVarNotAllowedError``
(from ``juturna.components.exceptions``) when the pipeline is created, before
anything is written to disk.
