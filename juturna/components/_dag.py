import typing
from collections import deque


class DAG:
    def __init__(self) -> None:
        self._adj: dict[str, set[str]] = {}
        self.edges: list[tuple[str, str]] = []

    def add_node(self, node: str) -> None:
        self._adj.setdefault(node, set())

    def add_edge(self, src: str, dst: str) -> None:
        if src not in self._adj or dst not in self._adj:
            raise ValueError(
                f"Source node '{src}' or destination node '{dst}' not in DAG"
            )
        self.edges.append((src, dst))
        self._adj[src].add(dst)

    def has_cycle(self) -> bool:
        in_deg = self.in_degree()
        queue = [n for n in self._adj if in_deg[n] == 0]
        visited = 0

        while queue:
            cur = queue.pop()
            visited += 1

            for neigh in self._adj[cur]:
                in_deg[neigh] -= 1

                if in_deg[neigh] == 0:
                    queue.append(neigh)

        return visited != len(self._adj)

    def in_degree(self) -> dict[str, int]:
        deg: dict[str, int] = {n: 0 for n in self._adj}

        for _, dst in self.edges:
            deg[dst] += 1

        return deg

    def out_degree(self) -> dict[str, int]:
        deg: dict[str, int] = {n: 0 for n in self._adj}

        for src, _ in self.edges:
            deg[src] += 1

        return deg

    def BFS(self) -> list[list[str]]:
        in_deg: dict[str, int] = self.in_degree()
        queue: deque[str] = deque(
            [node for node in self._adj if in_deg[node] == 0]
        )
        layers: list[list[str]] = []

        while queue:
            current_level: list[str] = []
            level_size: int = len(queue)

            for _ in range(level_size):
                node = queue.popleft()
                current_level.append(node)

                for neighbor in self._adj[node]:
                    in_deg[neighbor] -= 1

                    if in_deg[neighbor] == 0:
                        queue.append(neighbor)

            layers.append(current_level)

        return layers

    def as_dict(self) -> dict[str, typing.Any]:
        return {
            'edges': self.edges,
            'in_degree': self.in_degree(),
            'out_degree': self.out_degree(),
            'layers': self.BFS(),
        }
