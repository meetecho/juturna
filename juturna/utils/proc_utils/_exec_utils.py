def safe_exec(f):
    """
    Safely execute node methods
    Use this decorator when marking node methods that should not stop the node
    execution when an unpredictable exception is raised.
    """

    def wrapper(*args, **kwargs):
        caller = args[0]

        try:
            f(*args, **kwargs)
        except Exception as e:
            caller.logger.error(f'exception in update: {e}')

    return wrapper
