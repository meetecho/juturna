from collections.abc import Callable


def passthrough(sources: dict) -> dict:
    """
    Relay every message as soon as it is available

    This synchroniser simply marks every message stored in `source` as to be
    delivered, regardless of number, timestamp, or creator.
    """
    return {source: list(range(len(sources[source]))) for source in sources}


_SYNCHRONISERS: dict[str, Callable | None] = {
    'passthrough': passthrough,
    'local': None,
}
