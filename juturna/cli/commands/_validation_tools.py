import warnings
import json
import typing

from juturna.components._dag import DAG


class Check:
    """
    A validation rule. It passes when its function returns, fails when the
    function raises, and is skipped when a check it requires did not pass.
    """

    def __init__(
        self,
        name: str,
        func: typing.Callable,
        requires: tuple[str, ...] = (),
    ):
        self.name = name
        self.func = func
        self.requires = requires
        self.ok: bool | None = None
        self.error: str | None = None
        self.warnings: list[str] = list()

    @property
    def skipped(self) -> bool:
        return self.ok is None

    def __call__(self, *args, **kwargs) -> bool:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')

            try:
                self.func(*args, **kwargs)
                self.ok = True
            except ValidationError as exc:
                self.ok, self.error = False, str(exc)
            except Exception as exc:
                # a broken configuration can make a check fail in ways it did
                # not foresee: still a failed check, not a traceback
                self.ok = False
                self.error = f'{type(exc).__name__}: {exc}'

        self.warnings = [str(w.message) for w in caught]

        return self.ok


class ValidationPipe:
    def __init__(self):
        self._checks: list = []
        self.dag: DAG | None = None

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self._checks)

    @property
    def checks(self) -> list:
        return list(self._checks)

    def add_check(self, check: Check, active=True):
        if active:
            self._checks.append(check)

        return self

    def run_checks(self, *args, **kwargs):
        """
        Run the checks in order, passing them the same arguments. A check runs
        only if the checks it requires passed, so it can rely on what they
        verified.
        """
        passed = set()

        for check in self._checks:
            runnable = all(name in passed for name in check.requires)

            if runnable and check(*args, **kwargs):
                passed.add(check.name)

            print(_report_line(check))

            for message in check.warnings:
                print(f'  warning: {message}')

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            'success': self.ok,
            'checks': [
                {
                    'name': c.name,
                    'success': c.ok,
                    'skipped': c.skipped,
                    'error': c.error,
                    'warnings': c.warnings,
                }
                for c in self.checks
            ],
            'dag': self.dag.as_dict() if self.dag else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


def _report_line(check: Check) -> str:
    if check.skipped:
        return f'- {check.name}: skipped'

    if not check.ok:
        return f'\N{BALLOT X} {check.name}: {check.error}'

    return f'\N{CHECK MARK} {check.name}'


class ValidationError(RuntimeError):
    """Raised when any validation rule fails."""


def warn(msg: str) -> None:
    warnings.warn(msg, stacklevel=2)
