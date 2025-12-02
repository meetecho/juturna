import warnings
import json
import typing

from juturna.components._dag import DAG


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

            print(f'\N{CHECK MARK} {check.name}')

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
