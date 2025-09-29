import warnings
import json
import typing


class Check:
    def __init__(self, name: str, func: typing.Callable):
        self.name = name
        self.func = func
        self.ok: bool | None = None

    def __call__(self, *args, **kwargs) -> bool:
        self.ok = bool(self.func(*args, **kwargs)) | True


class ValidationPipe:
    def __init__(self):
        self._checks: list = []
        self.results: list = []
        self.dag: DAG | None = None

    @property
    def ok(self) -> bool:
        return all(c[0].ok for c in self._checks)

    @property
    def checks(self) -> list:
        return [c[0] for c in self._checks]

    def add_check(self, *args, active=True, **kwargs):
        check = args[0]

        if active:
            self._checks.append((check, args[1:], kwargs))

        return self

    def run_checks(self):
        for check, args, kwargs in self._checks:
            self.results.append((check.name, check(*args, **kwargs)))

            print(f'\N{check mark} {check.name} ciao')

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            'success': self.ok,
            'checks': [{'name': c.name, 'success': c.ok} for c in self.checks],
            'dag': self.dag.as_dict() if self.dag else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class ValidationError(RuntimeError):
    """Raised when any validation rule fails."""


def warn(msg: str) -> None:
    warnings.warn(msg, stacklevel=2)


class DAG:
    def __init__(self) -> None:
        self._adj: dict[str, set[str]] = {}
        self.edges: list[tuple[str, str]] = []

    def add_edge(self, src: str, dst: str) -> None:
        self.edges.append((src, dst))
        self._adj.setdefault(src, set())
        self._adj.setdefault(dst, set())
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

    def as_dict(self) -> dict[str, typing.Any]:
        return {
            'edges': self.edges,
            'in_degree': self.in_degree(),
            'out_degree': self.out_degree(),
        }
