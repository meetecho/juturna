.. _reference_constants:

Constants and environment variables
===================================

Juturna reads a few settings from the environment when it is imported. Each
has a default, used when the variable is not set.

.. list-table::
   :header-rows: 1
   :widths: 40 12 48

   * - Variable
     - Default
     - Meaning
   * - ``JUTURNA_MAX_QUEUE_SIZE``
     - ``999``
     - Messages the input queue of a node can hold. When it is full, the
       nodes sending to it wait.
   * - ``JUTURNA_THREAD_JOIN_TIMEOUT``
     - ``2.0``
     - Seconds a node thread is given to exit when the node is killed.
   * - ``JUTURNA_SOURCE_MAX_BACKOFF``
     - ``5.0``
     - Longest wait, in seconds, between two calls of a source function that
       keeps failing.
   * - ``JUTURNA_TELEMETRY_BATCH_SIZE``
     - ``10``
     - Telemetry records a node collects before handing them over.
   * - ``JUTURNA_PAYLOAD_SIZE_MAX_VISITS``
     - ``1000``
     - Objects visited at most when computing the size of an
       ``ObjectPayload`` for telemetry.
   * - ``JUTURNA_ENV_VAR_PREFIX``
     - ``$JT_ENV_``
     - Prefix that marks a configuration value as the name of an
       environment variable.

Set them before starting Juturna:

.. code-block:: console

    $ export JUTURNA_MAX_QUEUE_SIZE=2000
    $ python -m juturna launch --config pipeline.json

The value must convert to the type of the default: a value that does not
(``fast`` for ``JUTURNA_THREAD_JOIN_TIMEOUT``) raises ``RuntimeError`` at
import.

In code, the values are in ``juturna.meta``:

.. code-block:: python

    >>> import juturna as jt
    >>> jt.meta.JUTURNA_MAX_QUEUE_SIZE
    999

One more variable is read by the pipeline service only:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Meaning
   * - ``JUTURNA_SERVICE_TOKEN``
     - The token clients of ``juturna serve`` must send. When it is not
       set, the service generates one at startup.
