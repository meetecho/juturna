Constants and environment
=========================

Juturna uses a set of global constants to manage internal configurations, such
as plugin locations, hub repositories, and threading timeouts. While these
constants have sensible defaults, you can override them using environment
variables to suit your deployment needs.

This guide explains how to modify these configurations and ensures your
environment variables are typed correctly.

Using constants
---------------

You can access Juturna constants using the `meta` module:

.. code-block:: python

    >>> import juturna as jt
    >>> dir(jt.meta)
    ['JUTURNA_BASE_REPO',
     'JUTURNA_CACHE_DIR',
     'JUTURNA_HUB_TOKEN',
     'JUTURNA_HUB_URL',
     'JUTURNA_LOCAL_PLUGIN_DIR',
     'JUTURNA_MAX_QUEUE_SIZE',
     'JUTURNA_THREAD_JOIN_TIMEOUT',
     ...
    ]
    >>> jt.meta.JUTURNA_BASE_REPO
    https://github.com/meetecho/juturna

Overriding defaults
-------------------

To change a configuration, export the variable in your shell before running
Juturna.

.. code-block:: bash

    # changing the cache directory and increasing the queue size
    export JUTURNA_CACHE_DIR="/tmp/juturna_cache"
    export JUTURNA_MAX_QUEUE_SIZE="2000"

    # launch your pipeline
    python -m juturna launch --config my_pipeline.json

.. admonition:: Type validation (|version|-|release|)
    :class: :WARNING:

    Juturna enforces strict type checking on environment variables. The system
    attempts to cast your environment variable to the type of the default
    value.

    If you provide a value that cannot be converted (for example, providing a
    string "fast" for the integer ``JUTURNA_THREAD_JOIN_TIMEOUT``), the system
    will log an error and raise a ``RuntimeError``.

Handling boolean variables
--------------------------

When setting configuration flags that are boolean, Juturna parses specific
string values to determine truthiness.

To set a boolean variable to **True**, use one of the following case-insensitive
values: ``true``, ``1``, and ``yes``. Any other value will be interpreted as
**False** (unless it fails type conversion).

.. code-block:: bash

    # enabling a hypothetical boolean flag
    export JUTURNA_BOOL_FLAG="yes"

Available configuration variables
---------------------------------

If a variable is not set, Juturna falls back to the default values defined in
``juturna.meta._constants``.

You can customize the following variables in your environment.

**Repository and Hub Settings**

* ``JUTURNA_BASE_REPO``: The base URL for the Juturna repository.
    * **Default**: ``https://github.com/meetecho/juturna``
* ``JUTURNA_HUB_URL``: The API URL used to query and download plugins.
    * **Default**: ``https://api.github.com/repos/meetecho/juturna/contents/plugins/``
* ``JUTURNA_HUB_TOKEN``: An authentication token for the Hub.
    * **Default**: Empty string

**File System Paths**

* ``JUTURNA_CACHE_DIR``: The directory where downloaded plugins are cached.
    * **Default**: ``~/.cache/juturna`` (user's home directory)
* ``JUTURNA_LOCAL_PLUGIN_DIR``: The directory used for local plugin discovery.
    * **Default**: ``./plugins``

**Performance Tuning**

* ``JUTURNA_MAX_QUEUE_SIZE``: The maximum size of the internal queues used by nodes.
    * **Default**: ``999``
* ``JUTURNA_THREAD_JOIN_TIMEOUT``: The time (in seconds) to wait for threads to join during a stop procedure.
    * **Default**: ``2.0``

.. admonition:: Hub-related constants and hub features are not ready for use (|version|-|release|)
    :class: :ERROR:

    Hub features are still in development, so you should expect breaking changes
    and bugs. If you find any of the latter, please report them on GitHub. We
    are working hard to make the hub a reality, and we are looking for your
    feedback to make it better.

Working with env variables
--------------------------

Whenever a node should be configured with environment variables (imagine a node
that works with a secret key set on the environment within a container), juturna
is capable of filling in those configuration entries by picking up their values
from the environment variables.

Take for instance a sink node that requires in its configuration a secret token:

.. code-block:: json

    {
      "name": "destination",
      "type": "sink",
      "mark": "authenticated_sink",
      "configuration": {
        "endpoint": "127.0.0.1",
        "secret_token": "plain_token_is_dangerous!"
      }
    }

To avoid this, we might want to use an environment variable called
``AUTH_TOKEN``, provided from somewhere else. In this case, it is enough to
replace the item in the configuration with:

.. code-block:: json

    {
      "name": "destination",
      "type": "sink",
      "mark": "authenticated_sink",
      "configuration": {
        "endpoint": "127.0.0.1",
        "secret_token": "$JT_ENV_AUTH_TOKEN"
      }
    }

In short: environment variables used in configuration should be prefixed with
``$JT_ENV``.
