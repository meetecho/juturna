import inspect

from typing import Any

from juturna.telemetry._base import TelemetryContext
from juturna.telemetry._base import TelemetryManager
from juturna.telemetry.browser import BrowserTelemetry
from juturna.telemetry.csv import CsvTelemetry
from juturna.telemetry.memory import MemoryTelemetry
from juturna.transport import TransportBackend
from juturna.transport import get_transport


# Any: every manager has options of its own, which no common constructor
# signature can express
_MANAGERS: dict[str, Any] = {
    'browser': BrowserTelemetry,
    'csv': CsvTelemetry,
    'memory': MemoryTelemetry,
}


def _resolve(
    spec: dict | None, transport_cls: type[TransportBackend]
) -> tuple[type[TelemetryManager], dict] | None:
    if spec is None:
        return None

    if not isinstance(spec, dict):
        raise ValueError(
            f'telemetry must be a dict with a "name", got '
            f'{type(spec).__name__}: use {{"name": "csv", "target": "..."}}'
        )

    options = dict(spec)
    name = options.pop('name', None)

    if not isinstance(name, str):
        raise ValueError(
            f'telemetry needs a name, available: {list(_MANAGERS)}'
        )

    if name not in _MANAGERS:
        raise ValueError(
            f'unknown telemetry manager: {name!r}, available: {list(_MANAGERS)}'
        )

    manager_cls = _MANAGERS[name]

    try:
        # None stands for the context, which the pipeline provides
        inspect.signature(manager_cls).bind(None, **options)
    except TypeError as exc:
        raise ValueError(
            f'invalid options for the {name!r} telemetry: {exc}'
        ) from exc

    missing = manager_cls.requires - getattr(
        transport_cls, 'capabilities', frozenset()
    )

    if missing:
        raise ValueError(
            f'the {name!r} telemetry requires {sorted(missing)}, which the '
            f'{transport_cls.__name__} transport does not offer'
        )

    return manager_cls, options


def get_telemetry(
    spec: dict | None, ctx: TelemetryContext
) -> TelemetryManager | None:
    """
    Build the telemetry manager a pipeline asks for.

    Parameters
    ----------
    spec : dict | None
        The ``telemetry`` entry of the pipeline configuration: a dictionary
        with the ``name`` of the manager and its options. ``None`` means the
        telemetry is off.
    ctx : TelemetryContext
        The context of the pipeline.

    Returns
    -------
    TelemetryManager | None
        A new manager, or ``None`` if the telemetry is off.

    Raises
    ------
    ValueError
        If the configuration does not ask for a registered manager with
        options it accepts, or the manager needs something the transport
        does not offer.

    """
    resolved = _resolve(spec, type(ctx.transport))

    if resolved is None:
        return None

    manager_cls, options = resolved

    return manager_cls(ctx, **options)


def check_pipeline_telemetry(pipeline: dict) -> None:
    """
    Check the telemetry of a pipeline configuration.

    The transport and the manager are built and dropped: their constructors
    validate the options and hold no resource (the csv file is opened on
    start).

    Parameters
    ----------
    pipeline : dict
        The ``pipeline`` entry of a pipeline configuration.

    Raises
    ------
    ValueError
        If the transport or the telemetry cannot be built from it.

    """
    transport = get_transport(pipeline.get('transport'))
    ctx = TelemetryContext(transport, 'main', pipeline.get('folder', '.'))

    get_telemetry(pipeline.get('telemetry'), ctx)
