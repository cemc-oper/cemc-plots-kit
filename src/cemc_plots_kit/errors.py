"""Stable task-runtime error categories."""

from __future__ import annotations

from pathlib import Path

import reki


def classify_error(error: Exception, *, storage_base: str | None = None) -> str:
    """Classify errors without treating corruption or ambiguity as missing."""
    if isinstance(error, reki.DataNotFoundError):
        return "field_missing"
    if isinstance(error, reki.MultipleFieldsMatchedError):
        return "multiple_fields"
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
