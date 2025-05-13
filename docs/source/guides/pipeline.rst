#####################
Pipeline fundamentals
#####################

A pipeline can be created starting from a configuration file::

  import juturna as jt


  pipe = jt.components.Pipeline.from_json('config.json')

Similarly, the ``Pipeline`` constructor can accept a dictionary object::

  import json
  import juturna as jt


  with open('config.json', 'r') as f:
    config = json.load(f)

  pipe = jt.components.Pipeline(config)

Once a pipeline is created, a number of properties can be queried on it::

  # get the pipeline id
  pipe.pipe_id

  # get the pipeline execution folder
  pipe.pipe_folder

  # get the pipeline status
  pipe.status

Pipeline lifecycle
==================

A pipeline object provides 4 main methods to manage its status:

- ``warmup``: the concrete nodes in the pipeline are instantiated, and links
  are created (warmup may be time-consuming if there are nodes that require
  resources such as inference models)
- ``start``: after warmup, the pipeline starts its workflow
- ``stop``: the running pipeline is stopped
- ``destroy``: if needed, the pipeline can call this method if any kind of
  custom memory management should be performed by any of its composing nodes

::

   import juturna as jt


   pipe = jt.components.Pipeline.from_json('config.json')

   pipe.warmup()
   pipe.start()
   ...
   pipe.stop()
   pipe.destroy()

These methods will simply invoke their homonimous methods within the nodes in a
pipeline.

Configuration skeleton
======================

::

  {
    "version": "0.1.0",
    "plugins": ["./plugins"],
    "pipeline": {
      "name": "pipeline_name",
      "id": "pipeline_id",
      "folder": "./pipeline_folder",
      "nodes": [ ],
      "links": [ ]
    }
  }

+--------------+------------+---------------------------+
| field name   | type       | description               |
+==============+============+===========================+
| ``version``  | ``str``    | pipeline semantic version |
+--------------+------------+---------------------------+
| ``plugins``  | ``list``   | pluin folders scanned for |
|              |            | nodes at creation time    |
+--------------+------------+---------------------------+
| ``pipeline`` | ``object`` | actual target pipeline    |
+--------------+------------+---------------------------+

- ``version``: string with the pipeline semantic version (consider this field
  reserved, even if it is currently not used, nor version control enforced)
- ``plugins``: list of plugin folders, all of them will be automatically
  scanned when nodes are created (order is important: folders are scanned in
  the order they are included in the list, and scanning will stop at the first
  node name match)
- ``pipeline``: object containing the actual pipeline to build

Pipeline configuration fields
-----------------------------

+--------------+------------+-----------------------------+
| field name   | type       | description                 |
+==============+============+=============================+
| ``name``     | ``str``    | pipeline symbolic name      |
+--------------+------------+-----------------------------+
| ``id``       | ``str``    | pipeline unique identifier  |
+--------------+------------+-----------------------------+
| ``folder``   | ``str``    | folder where a running      |
|              |            | pipeline can save artifacts |
|              |            | or any other produced       |
|              |            | resource that should be     |
|              |            | persistent on disk          |
+--------------+------------+-----------------------------+
| ``nodes``    | ``list``   | list of nodes in the pipe   |
|              |            | (order is not important)    |
+--------------+------------+-----------------------------+
| ``links``    | ``list``   | list of links in the pipe   |
|              |            | (order is important)        |
+--------------+------------+-----------------------------+

- ``folder``: in this folder, the pipeline will create a sub-folder for each
  one of the nodes in the pipeline
- ``nodes``: this is the list of the nodes composing the pipeline, where each
  node item should contain the actual configuration for that node (please refer
  to the :doc:`node doc page <./custom_nodes>` to read the node
  documentation).
- ``links``: links are objects that only contain a ``from`` key and a ``to``
  key, representing respectively the source and the destination of a connection
  within the pipeline. Links are built using node names.

Full pipeline example
---------------------

::

   {
     "version": "1.0",
     "plugins": ["./plugins"],
     "pipeline": {
       "name": "pose_tracker",
       "id": "demo_pipeline",
       "folder": "./running",
       "nodes": [
       {
         "name": "0_src",
         "type": "source",
         "mark": "video_camera",
         "repository": "hub",
         "configuration": {
           "capture_device_id": 0,
           "mode": "still",
           "rate": 25,
           "width": 1280,
           "height": 720
         }
       },
       {
         "name": "1_pose",
         "type": "proc",
         "mark": "tracker_yolo",
         "repository": "hub",
         "configuration": {
           "model": "yolo11x-pose",
           "device": "cuda",
           "classes": ["person"],
           "confidence": 0.25
         }
       },
       {
         "name": "2_ffmpeg",
         "type": "sink",
         "mark": "videostream_ffmpeg",
         "configuration": {
           "dst_host": "127.0.0.1",
           "dst_port": 8888,
           "in_width": 1280,
           "in_height": 720
         }
       }],
       "links": [
       {
         "from": "0_src",
         "to": "1_pose"
       },
       {
         "from": "1_pose",
         "to": "2_ffmpeg"
       }]
     }
   }
