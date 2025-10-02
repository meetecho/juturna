#################
Build and install
#################

The following dependencies are required to use Juturna:

+-------------+------------+-------------------------------------------------+
| dependency  | type       | notes                                           |
+=============+============+=====================+===========================+
| ``python``  | ``>=3.12`` | building version is 3.12, still to be tested on |
|             |            | 3.13 with GIL disabled                          |
+-------------+------------+-------------------------------------------------+
| ``libsm6``  | ``system`` |                                                 |
+-------------+------------+-------------------------------------------------+
| ``libext6`` | ``system`` |                                                 |
+-------------+------------+-------------------------------------------------+
| ``ffmpeg``  | ``system`` |                                                 |
+-------------+------------+-------------------------------------------------+

Juturna is currently available as a opensource codebase, but not yet published
on PyPi. To install it on your system, first clone the repository, then use
``pip`` to install it (assuming you are working in a virtual environment)::

  (venv) $ git clone https://github.com/meetecho/juturna
  (venv) $ pip install ./juturna

In case you want to include all the development dependencies in the
installation, specify the ``dev`` group::

  (venv) $ pip install "./juturna[dev]"

Alternatively, you can manually install the required dependencies, and just
import the ``juturna`` module from within the repository folder::

  (venv) $ pip install av ffmpeg-python opencv-python numpy requests websockets
  (venv) $ python
  >>> import juturna as jt

Build the documentation
=======================
If you want to build the documentation locally, install Juturna including the
dev dependencies, then within the repository folder run the following::

  (venv) $ cd docs && sphinx-build -b html source build/html

In case you are actively working on the documentation and need automatic
building, you can use ``sphinx-autobuild`` (already included in the dev
dependencies)::

  (venv) $ cd docs
  (venv) $ sphinx-autobuild source build/html

Tests
=====
To run the tests, you need to install Juturna with the ``dev`` dependencies,
which include ``pytest``, then from the repository root folder::

  (venv) $ pytest ./test

Docker image
============
In the Juturna repository you will find a ``Dockerfile`` that can be used to
create a base Juturna image. To build it, symply navigate within the repo
folder and run::

  $ docker build -t juturna:latest .
