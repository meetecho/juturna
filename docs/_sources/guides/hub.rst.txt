###########
Juturna Hub
###########

:bdg-warning:`warning`  **Hub features are still in development, so you should
expect breaking changes and bugs. If you find any of the latter, please report
them on GitHub. We are working hard to make the hub a reality, and we are
looking for your feedback to make it better.**

Custom nodes and pipelines can be shared with the community and accesed through
the Juturna Hub. The hub is a repository of community-contributed nodes and
pipelines that can be downloaded and used in your own projects.

Hub APIs
========
The hub APIs are available in the :code:`juturnat.hub` module. For a more
detailed description of the APIs, refer to the :doc:`API doc page <../apis/index>`.

You can list all the available plugins as follows::
    
    import juturna as jt
    

    plugins = jt.hub.list_plugins()

This will return a dictionary with the following keys:

- :code:`nodes`: a list of all the available nodes;
- :code:`pipelines`: a list of all the available pipelines;

To download a node, simply run::
    
    import juturna as jt
    

    jt.hub.download_node('node_name', destination_folder='./plugins')

This will download the node and install it in your local Juturna installation.

Similarly, to download a pipeline, run::
    
    import juturna as jt
    

    jt.hub.download_pipeline('pipeline_name', destination_folder='./pipelines')

Downloading a pipeline has the effect of downloading all the nodes that are
required by that pipeline.

Hub CLI
==========
The hub module is accessible from the command line as well. You can use the
module to list and download plugins as follows::
    
    $ python -m juturna.hub list_plugins
    $ python -m juturna.hub download --node node_type/_node_name
    $ python -m juturna.hub download --pipe pipe_name --destionation ./plugins

Custom plugin repository and authentication tokens
=================================================
By default, the hub will download plugins from the Juturna Hub repository. That
means, it will look into the Juturna GitHub repository and scan the ``plugins``
folder for any available plugins. If you want to use your own custom plugin
repository, you can do so by setting the environment variable
:code:`JUTURNA_HUB_REPO` to the URL of your custom repository. For example::
    
    JUTURNA_HUB_REPO='your/custom/repo' python your_script.py

In case your repository is private, you can set the environment variable
``JUTURNA_HUB_TOKEN`` to the authentication token that will be used to access
the repository. For example::

    JUTURNA_HUB_REPO='your/custom/repo' JUTURNA_HUB_TOKEN='your_token' python your_script.py

Authenticated requests require the ``authenticate`` option to be passed to the
:code:`hub` function you are using. For example::
    
    import juturna as jt
    

    jt.hub.list_plugins(authenticate=True)
    jt.hub.download_node('node_name', authenticate=True)

    # the target repository can be specified here
    jt.hub.list_plugins(repository_url='your_custom_repo', authenticate=True)
    jt.hub.download_node('node_name', repository_url='your_custom_repo', authenticate=True)

Similarly, from the command line, you can specify a request is authenticated as
follows:::
    
    $ python -m juturna.hub --authenticate list_plugins
    $ python -m juturna.hub --authenticate download --node node_type/_node_name