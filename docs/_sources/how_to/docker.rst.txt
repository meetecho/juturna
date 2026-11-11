Build a Docker image
====================

In the Juturna repository you will find a ``Dockerfile`` that can be used to
create a base Juturna image. To build it, navigate within the repo
folder and run:

.. code-block:: console

    $ docker build -t juturna:latest .

The image contains the core Juturna library, installed from the repository
folder, with the ``full`` optional group (``httpwrapper``, ``pipebuilder`` and
``warp``). It contains no nodes: install ``juturna-nodes``, or your own node
packages, in an image built on top of it.

The optional groups can be changed with the ``JT_VERSION`` build argument.
To install the core package only:

.. code-block:: console

    $ docker build --build-arg JT_VERSION="" -t juturna:latest .

Or a single group:

.. code-block:: console

    $ docker build --build-arg JT_VERSION="[warp]" -t juturna:latest .

Dev image
---------

While working on Juturna itself, it is handy to have a container that
reinstalls the library whenever its code changes. This can be automated with
the following files:

.. tab-set::

    .. tab-item:: dockerfile

        .. code-block:: dockerfile

            FROM python:3.12-slim

            RUN mkdir -p /juturna_dev

            RUN apt-get update -y && apt-get install -y --no-install-recommends \
                git jq libgl1 libglib2.0-0 libsm6 libxext6 ffmpeg \
                libinotifytools0 inotify-tools \
                gcc g++

            RUN pip install --no-cache-dir --upgrade pip

            COPY ./watcher.sh /usr/local/bin

            WORKDIR /juturna_dev

    .. tab-item:: watcher.sh

        .. code-block:: bash

            #!/bin/bash

            pip install --no-cache /juturna
            echo "Starting file watcher..."

            while inotifywait -r -e modify,create,delete /juturna \
                              --exclude '(__pycache__|\.pyc|\.git)'; do
                echo "Changes detected, reinstalling..."
                pip install --no-cache /juturna
                echo "Reinstall complete"
            done

    .. tab-item:: run.sh

        .. code-block:: bash

            #!/bin/bash

            docker stop juturna_dev
            docker rm juturna_dev

            docker build -t juturna_dev:latest .

            docker run \
                   -d \
                   --name juturna_dev \
                   --network host \
                   --volume $1:/juturna \
                   juturna_dev:latest \
                   /usr/local/bin/watcher.sh

            sleep 3

            docker exec -ti juturna_dev bash

Execute the ``run.sh`` script with:

.. code-block:: console

    $ ./run.sh <PATH_TO_JUTURNA>
