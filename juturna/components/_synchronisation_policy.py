from typing import Protocol


class SynchronisationPolicy(Protocol):
    def next_batch(self, sources: dict) -> dict: ...


class PassthroughPolicy(SynchronisationPolicy):
    """Return whatever is stored in the source buffer"""

    def next_batch(self, sources: dict) -> dict:
        return {
            creator: list(range(len(sources[creator]))) for creator in sources
        }


_POLICIES = {'passthrough': PassthroughPolicy}
