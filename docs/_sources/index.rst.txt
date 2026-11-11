.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Tutorials

   tutorials/first_pipeline

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: How-to guides

   how_to/index
   how_to/install
   how_to/create_nodes
   how_to/create_pipelines
   how_to/environment
   how_to/serve_pipelines
   how_to/remotise_node
   how_to/observe
   how_to/docker
   how_to/migrate_from_2

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Reference

   reference/configuration
   reference/cli
   reference/http_api
   reference/constants
   apis/explore

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Explanation

   explain/rationale
   explain/entities_overview
   explain/pipelines
   explain/nodes
   explain/messages
   explain/remote

|version-badge|

Juturna's documentation
=======================

.. .. image:: ./_static/img/logo_dark_alt_transparent.svg
..    :alt: juturna
..    :width: 30%
..    :align: center

.. \

.. image:: https://img.shields.io/github/license/meetecho/juturna?style=for-the-badge
    :alt: License

.. image:: https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fmeetecho%2Fjuturna%2Frefs%2Fheads%2Fmain%2Fpyproject.toml&style=for-the-badge&color=green
   :alt: Python Version from PEP 621 TOML

.. image:: https://img.shields.io/github/stars/meetecho/juturna?style=for-the-badge
    :alt: Stars

.. image:: https://img.shields.io/github/forks/meetecho/juturna?style=for-the-badge
    :alt: Forks

.. image:: https://img.shields.io/github/issues/meetecho/juturna?style=for-the-badge
    :alt: Issues

----

Energise your multimedia data prototyping with **Juturna**: design, implement,
execute and manipulate real-time pipelines in minutes!

.. grid:: 2

    .. grid-item::
        .. card:: ``jt/tutorials``
            :link: tutorial
            :link-type: ref

            New to Juturna? Build and run your first pipeline, one step at a
            time.

    .. grid-item::
        .. card:: ``jt/how_to``
            :link: howto
            :link-type: ref

            Recipes for the tasks you will meet: writing nodes, running a
            service, moving a node to another machine, upgrading from 2.x.

.. grid:: 2

    .. grid-item::
        .. card:: ``jt/reference``
            :link: reference
            :link-type: ref

            The facts: configuration file, CLI, HTTP API, constants and the
            Python API.

    .. grid-item::
        .. card:: ``jt/explain``
            :link: rationale
            :link-type: ref

            The ideas behind Juturna: pipelines, nodes, messages, and how
            they work together.

.. grid:: 1

    .. grid-item::

            .. card::
                :text-align: center

                :fas:`meetecho`

                Juturna is brewed with love by the awesome team of
                `Meetecho <https://www.meetecho.com/en/>`_. Come and say hi!

Nodes ready to use (audio and video sources, transcription, detection,
notifiers) live in their own package,
`juturna-nodes <https://github.com/meetecho/juturna_nodes>`_.

Coming from Juturna 2.x? Start from the :ref:`migration guide <migrate_from_2>`.

Take a look at the `GitHub project <https://github.com/meetecho/juturna>`_ if
you want to explore the code.

Feel like contributing? Please refer to our
`guidelines <https://github.com/meetecho/juturna/blob/main/CONTRIBUTING.md>`_.
