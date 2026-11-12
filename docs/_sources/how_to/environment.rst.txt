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

For this reason the pipeline service (``juturna serve``) reads no variable by
default: a configuration that references one is refused with ``403``. There
are two ways to give its clients the variables they need.

Give the service an environment file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Put the variables for the pipelines in a file, one ``NAME=value`` per line:

.. code-block:: bash

    # pipelines.env
    AUTH_TOKEN=s3cr3t
    MODEL_DIR=/srv/models
    GREETING="hello world"   # quotes keep spaces and the # sign

and point the service to it:

.. code-block:: console

    $ chmod 600 pipelines.env
    $ python -m juturna serve -p 8000 -f ./pipelines --env-file pipelines.env

Configurations can now read ``$JT_ENV_AUTH_TOKEN`` and the other variables of
the file, and nothing else. Two things make the file the better choice:

- it is read again every time a pipeline is created, so you can **add or
  change a variable without restarting the service**. Pipelines that already
  exist keep the values they were created with;
- its variables are handed to the pipelines only. They never enter the
  environment of the service, and the variables of the service stay out of
  reach.

The file holds secrets: the service warns at startup when other users can
read it, and stops if it cannot parse it. Values are taken as written:
``$OTHER`` is not expanded, and a value cannot span several lines.

Allow variables of the service environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When the variables are already in the environment of the service (set by a
container, for example), allow them with ``--allow-env``. It takes a name or
a pattern, and can be repeated:

.. code-block:: console

    $ python -m juturna serve -p 8000 -f ./pipelines \
             --allow-env AUTH_TOKEN --allow-env 'MODEL_*'

``--allow-env '*'`` allows every variable. It is meant for a service whose
only client is you: any client can then read any secret of the service
process, its token included.

With both options, a variable is looked up in the file first, then in the
environment if ``--allow-env`` lets it. Both cover the ``configuration`` and
the ``warp_configuration`` of a node.

In your own code
^^^^^^^^^^^^^^^^

The same controls are available when you build pipelines from configurations
you do not control:

.. code-block:: python

    import juturna as jt

    from juturna.utils.jt_utils import read_env_file


    pipeline = jt.components.Pipeline(
        config,
        allowed_env_vars=[],
        env_vars=read_env_file('pipelines.env'),
    )

``env_vars`` gives the pipeline its own variables, and ``allowed_env_vars``
lists the names or patterns it can read from the process environment (none
here; any, when the argument is left out). A configuration that reads any
other variable raises ``EnvVarNotAllowedError`` (from
``juturna.components.exceptions``) when the pipeline is created, before
anything is written to disk.
