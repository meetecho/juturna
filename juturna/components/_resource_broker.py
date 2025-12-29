from juturna.utils.net_utils import get_available_port


_RESOURCES = {'port': get_available_port, 'gpu': lambda: None}


def resources() -> list:
    return list(_RESOURCES.keys())


def get(resource: str, args: dict | None = None):
    if args is None:
        args = dict()

    return _RESOURCES[resource](**args)
