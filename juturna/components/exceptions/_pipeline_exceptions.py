"""
Pipeline lifecycle exceptions.

These are the only exceptions Pipeline raises for illegal lifecycle
transitions. They are owned by core (not by juturna.cli) so that Pipeline
stays the single, deterministic source of truth for state validation,
regardless of which layer (HTTP wrapper, PipelineManager, direct API use)
invokes it. Every exception subclasses RuntimeError, so existing
``except RuntimeError`` call sites keep working unchanged.
"""


class PipelineStateError(RuntimeError):
    """Base exception for illegal Pipeline lifecycle transitions."""

    def __init__(self, pipeline_name: str, message: str):
        """
        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline on which the illegal transition was
            attempted.
        message : str
            Human readable description of the illegal transition.

        """
        self.pipeline_name = pipeline_name

        super().__init__(message)


class PipelineNotReadyError(PipelineStateError):
    """Raised when start() is called before the pipeline was warmed up."""


class PipelineNotRunningError(PipelineStateError):
    """Raised when stop() is called on a pipeline that is not running."""


class PipelineAlreadyRunningError(PipelineStateError):
    """Raised when warmup() is called on a pipeline that is running."""


class PipelineStoppedError(PipelineStateError):
    """
    Raised when warmup() or start() is called on a stopped pipeline.

    A stopped pipeline cannot be resumed: it must be destroyed and a new
    pipeline created in its place.
    """


class PipelineDestroyedError(PipelineStateError):
    """
    Raised when a lifecycle operation is called on a destroyed pipeline.

    destroy() itself is exempted: calling it on an already destroyed
    pipeline is a no-op.
    """


class PipelineBusyError(PipelineStateError):
    """
    Raised when a lifecycle operation is called while another one is
    already in progress on the same pipeline.

    Only one of warmup()/start()/stop()/destroy() can be claimed at a time:
    the transition in flight owns the pipeline's internal state (nodes,
    DAG, node threads) until it completes, so a concurrent call cannot be
    safely evaluated against the pipeline's current status.
    """
