########
Messages
########

A message is a data container used to exchange data across nodes.

+---------------------+-----------------+----------------------------------+
| property            | type            | description                      |
+=====================+=================+==================================+
| ``self.creator``    | ``str``         | name or id of the creating node  |
+---------------------+-----------------+----------------------------------+
| ``self.version``    | ``int``         | message data version             |
+---------------------+-----------------+----------------------------------+
| ``self.payload``    | ``BasePayload`` | data to be transferred upstream  |
|                     |                 | in the pipeline                  |
+---------------------+-----------------+----------------------------------+
|  ``self.meta``      | ``dict``        | message metadata                 |
+---------------------+-----------------+----------------------------------+
| ``self.timers``     | ``dict``        | collection of timers to evaluate |
|                     |                 | performed data operations        |
+---------------------+-----------------+----------------------------------+

An empty message is created with:

- ``creator`` set to ``None``
- ``version`` set to ``-1``

The message payload is an object of type ``BasePayload`` (or any of its
derived types; see the :doc:`payload doc page <./payloads>`
for more details). When a message is created, its payload type should be
specified.


+----------------------------+---------------------+-------------------------+
| method                     | arguments           | description             |
+============================+=====================+=========================+
| ``Message.from_message()`` | ``(Message, bool)`` | create a message by     |
|                            |                     | copying another message |
+----------------------------+---------------------+-------------------------+
| ``self.to_dict()``         |                     | convert the message to  |
|                            |                     | a dictionary            |
+----------------------------+---------------------+-------------------------+
| ``self.to_json()``         |                     | convert the message to  |
|                            |                     | a json string           |
+----------------------------+---------------------+-------------------------+
| ``self.timer()``           | ``(str, float)``    | add timer to message    |
+----------------------------+---------------------+-------------------------+

Notes:

- currently, ``to_json()`` simply returns the ``json.dumps()`` on the
  dictionary version of a message; this means that generating a json string for
  the message will fail if the message payload is not serialisable using the
  encoder function provided as argument


Timers
======

In order to keep track of any operations performed to generate the data
contained in a message, a context manager, ``timeit``, is offered to
automatically create within the message ``timers`` dictionary a relevant entry.

::

   >>> m = Message()
   >>> with m.timeit('timer_name'):
   >>>     time.sleep(1)
   >>> m.timers
   {'timer_name': 1.001392364501953}

Alternatively, set a timer using the ``timer()`` method::

  >>> m = Message()
  >>> m.timer('timer_name', 1.1)
  >>> m.timers
  {'timer_name': 1.1}
