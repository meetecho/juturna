Install
=======

A small group of system dependecies are required on your system before you
start the installation process. If running Ubuntu or any Debian-based distros:

.. code-block:: console

    $ sudo apt install libsm6 libext6 ffmpeg

The simplest way to install Juturna is to fetch it from the official Python
Package Index (`PyPi <https://pypi.org/project/juturna/>`_). Assuming you are
working within a virtual environment, simply run:

.. code-block:: console

    (venv) $ pip install juturna

You can also fetch the Juturna source code from the
`GitHub repository <https://github.com/meetecho/juturna>`_ and install it
manually:

.. code-block:: console

    (venv) $ git clone https://github.com/meetecho.juturna
    (venv) $ pip install ./juturna

Extras
------

When installing Juturna, you can specify extra groups to include in the
installation. Groups that provide extra features are:

- ``httpwrapper``: CLI serving capabilities
- ``pipebuilder``: interactive CLI pipeline builder
- ``warp``: remotisation tools

Additionally, a number of extra groups are available to manage all the
development dependencies:

- ``doc``: Sphinx stuff, in case you want to compile the documentation
- ``dev``: everything you need to properly contribute to Juturna
- ``lint``: dependency to make sure your code is properly formatted
- ``test``: Juturna testing packages

.. admonition:: Warp tools are still experimental! (|version|-|release|)
    :class: :WARNING:

    There might be bits and pieces slightly out of place with the remotisation
    architecture, so please use the ``warp`` group only if you are
    experimenting!

Extra groups can be selected during the installation proess.

.. code-block:: console

    # only include a single optional group
    (venv) $ pip install -U 'juturna[dev]'

    # inclunde multiple optional groups
    (venv) $ pip install -U 'juturna[dev,httpwrapper]'

To simplify things, three meta-groups are also included:

- ``full`` installs ``httpwrapper``, ``pipebuilder`` and ``warp``
- ``dev_full`` installs ``doc``, ``dev``, ``lint``, and ``test``
- ``all`` installs ``full`` and ``dev_full``

Documentation building
----------------------

If you want to build the documentation locally, install Juturna including the
``dev`` group, then within the repository folder run the following:

.. code-block:: console

    (venv) $ cd docs && sphinx-build -b html ./source ./build/html

In case you are actively working on the documentation and need automatic
building, you can use ``sphinx-autobuild`` (already included in the ``dev``
group):

.. code-block:: console

    (venv) $ cd docs
    (venv) $ sphinx-autobuild ./source ./build/html

This will automatically trigger the building script whenever a file in the
``source`` folder is edited.

Testing
-------

To run the tests, you need to install Juturna with the ``dev`` group, which
include ``pytest``, then from the repository root folder:

.. code-block:: console

    (venv) $ pytest -vvv

Please consider that all the test cases concerning the Juturna Hub actively
interact with GitHub, and this can quickly drain the API quota. It is
recommended you disable them:

.. code-block:: console

    (venv) $ pytest -vvv --ignore ./tests/test_hub.py
