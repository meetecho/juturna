Install
=======

As of now (version |version|-|release|), Juturna is not yet published on the
Python Package Index, so the installation requires fetching it from the
`GitHub repository <https://github.com/meetecho/juturna>`_.

A small group of system dependecies are required on your system before you
start the installation process. If running Ubuntu or any Debian-based distros:

.. code-block:: console

    $ sudo apt install libsm6 libext6 ffmpeg

Once this is done, you can clone the repository and install it using ``pip``.
Assuming you are working within a virtual environment, simply run:

.. code-block:: console

    (venv) $ git clone https://github.com/meetecho.juturna
    (venv) $ pip install ./juturna

Alternatively, you can manually install the required Python dependencies, then
import the ``juturna`` module from within the repository folder:

.. code-block:: console

    (venv) $ pip install av ffmpeg-python opencv-python numpy requests websockets
    (venv) $ cd ./juturna
    (venv) $ python
    >>> import juturna as jt

Optional dependencies
---------------------

When installing Juturna, you can specify extra groups to include in the
installation. Currently available groups are:

- ``dev`` to get all the tools for testing and documentation,
- ``httpwrapper`` to get CLI serving capabilities.
- ``pipebuilder`` to get the interactive CLI pipeline builder

Extra groups can be selected during the installation proess.

.. code-block:: console

    # only include a single optional group
    (venv) $ pip install -U './juturna[dev]'

    # inclunde multiple optional groups
    (venv) $ pip install -U './juturna[dev,httpwrapper]'

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