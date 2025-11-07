Docker
======

In the Juturna repository you will find a ``Dockerfile`` that can be used to
create a base Juturna image. To build it, symply navigate within the repo
folder and run:

.. code-block:: console
    
    $ docker build -t juturna:latest .

The created image will include the core Juturna code, and all its plugins. You
can find them in the ``/root/juturna`` folder.

Dev image
---------

Should you require to build a Docker image for development purposes, you can do
so by adding a few extra items in the ``Dockerfile``. Whilst plugins do not
require reinstalling Juturna to be updated, changing the code does. This can be
automated with the following:

.. tab-set::

    .. tab-item:: dockerfile

        .. code-block:: dockerfile

            FROM python:3.12-slim
            
            RUN mkdir -p /juturna_dev

            COPY ./requirements.txt /juturna_dev

            RUN pip install -r /juturna_dev/requirements.txt

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

            while inotifywait -r -e modify,create,delete /juturna /jutest/plugins \
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
                   -vvv \
                   --name juturna_dev \
                   --network host \
                   --volume $1:/juturna \
                   juturna_dev:latest \
                   /usr/local/bin/./watch.sh

            sleep 3

            docker exec -ti juturna_dev bash

Execute the ``run.sh`` script with:

.. code-block:: console

    $ ./run.sh <PATH_TO_JUTURNA>