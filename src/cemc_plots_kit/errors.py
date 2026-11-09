"""Stable task-runtime error categories."""

from __future__ import annotations

from pathlib import Path

import reki
from cedar_graph.recipes.ensemble_product import MissingMemberError
from cedarkit.plots.workflow.runtime import PlanExecutionError


def execution_cause(error: Exception) -> Exception:
    """Keep workflow location separately while classifying the read failure."""
    while isinstance(error, PlanExecutionError) and error.cause is not None:
        error = error.cause
    return error


def is_missing_error(error: Exception) -> bool:
    """Business absence only; access, decode and service failures remain errors."""
    error = execution_cause(error)
    return isinstance(error, MissingMemberError) or (
        isinstance(error, (reki.QueryError, reki.SourceError, reki.CompletenessError))
        and error.code in {"no_match", "missing_fields"}
    )


def classify_error(error: Exception, *, storage_base: str | None = None) -> str:
    """Classify errors without treating corruption or ambiguity as missing."""
    error = execution_cause(error)
    if is_missing_error(error):
        return "field_missing"
    if isinstance(error, (reki.QueryError, reki.SourceError, reki.CompletenessError)):
        return error.code
    if isinstance(error, FileNotFoundError):
        if storage_base and not Path(storage_base).exists():
            return "mount_missing"
        return "file_missing"
    name = error.__class__.__name__
    if name == "IndexBuildError":
        return "index_error"
    if name in {"DecodeError", "DataArrayContractError"}:
        return "decode_error"
    if name in {"RenderError", "PlotRenderError"}:
        return "render_error"
    if name in {"PublishError", "ManifestPublishError"}:
        return "publish_error"
    return "op_error"
