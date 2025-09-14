#######
Logging
#######

Juturna offers a library-level logger called ``jt``, and a number of dynamic
child loggers for pipelines and nodes.

Setting a level on the root logger will propagate on all its child loggers.
However, loggers can be selectively enabled or disabled. So, for example::

    import logging

    import juturna as jt

    # loading a pipe named 'trx_pipe'
    pipe = jt.components.Pipeline.from_json('config.json')

    # this will set ERROR level on a pipe node called '4_dst'
    logging.getLogger('jt.trx_pipe.4_dst').setLevel(logging.ERROR)

    # this will set ERROR level on the entire pipe (including all the nodes)
    logging.getLogger('jt.trx_pipe').setLevel(logging.ERROR)

    # this will set ERROR level on the whole library (all pipes and nodes)
    logging.getLogger('jt').setLevel(logging.ERROR)

###############
Formatting logs
###############

Some formatters are conveniently shipped in Juturna to offer basic logging
formats. These can be changed with::

    import juturna as jt


    jt.utils.log_utils.formatter('colored')

Available formatters are:

- ``simple``: ``2025-09-14 09:08:38,412 - jt.demo.4_translate - INFO - message``
- ``colored``: ``2025-09-14 09:10:03,183 | INFO     | jt.demo.4_translate     | message``
- ``full``: ``2025-09-14 09:11:14 | INFO     | jt.demo.4_translate     | message``
- ``compact``: ``09:12:43 | I | jt.demo.4_translate     | message``
- ``development``: ``09:13:58 | INFO     |jt.demo.4_translate:39 | warmup() | message``
- ``minimal``: ``INFO: tokenizer: message``
- ``json``: ``{"timestamp": "2025-09-14T09:15:20.561188", "level": "INFO", "logger": "jt.demo.4_translate", "message": "message", "module": "translator_nllb", "function": "warmup", "line": 39}``

The default formatter is ``full``. It differs from the ``colored`` formatter as
the latter highlights with colours the logging level.