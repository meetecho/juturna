from enum import StrEnum
from enum import unique


@unique
class ComponentStatus(StrEnum):
    """
    Possible state values of a component.

    - ``NEW`` (``component_created``): a component was instantiated
    - ``CONFIGURED`` (``component_configured``): a component was configured,
      or, the ``configure()`` method was invoked on it
    - ``RUNNING`` (``component_running``): a component is running within a
      running pipeline, so, ``configure()`` and ``start()`` were previosuly
      invoked on it
    - ``STOPPED`` (``component_stopped``): a previously running component was
      stopped, so ``stop()`` was invoked on it
    """

    NEW = 'component_created'
    CONFIGURED = 'component_configured'
    RUNNING = 'component_running'
    STOPPED = 'component_stopped'
