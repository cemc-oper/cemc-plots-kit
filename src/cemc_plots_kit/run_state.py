"""Checkpoint identities and conservative reuse of completed local plot jobs."""

from __future__ import annotations

import hashlib
from importlib.metadata import distributions, version
import json
from pathlib import Path
import sys
from typing import Any


class ResumeError(ValueError):
    """An existing checkpoint cannot safely supply completed job results."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def installed_versions() -> dict[str, str]:
    """Pin the resolved dependency environment, including plotting libraries."""
    return {item.metadata["Name"].lower().replace("_", "-"): item.version
            for item in distributions()}


def recovery_identity(plan, task_file: Path, definitions) -> dict[str, Any]:
    """Pin configuration, compiled recipes, source resources and software."""
    compiled = json.dumps(plan.document, sort_keys=True, separators=(",", ":"), default=str)
    external_recipes = {}
    for job in plan.document["jobs"]:
        if Path(job["plot"]).suffix.lower() not in {".yaml", ".yml"}:
            continue
        path = Path(job["plot"])
        path = (Path(task_file).parent / path).resolve() if not path.is_absolute() else path
        try:
            external_recipes[str(path)] = _sha256(path)
        except OSError:
            # Missing/unreadable recipes remain normal static-plan failures.
            external_recipes[str(path)] = None
    return {
        "task_plan_identity": plan.identity,
        "compiled_plan_sha256": hashlib.sha256(compiled.encode()).hexdigest(),
        "task_file_sha256": _sha256(Path(task_file)),
        "external_recipes": external_recipes,
        "definitions": list(definitions),
        "software": {
            "python": sys.version,
            "packages": {name: version(name) for name in (
                "cedarkit-query", "reki", "cedarkit-comp", "cedarkit-plots",
                "cedar-graph", "cemc-plots-kit",
            )},
            "distributions": installed_versions(),
        },
    }


def output_information(outputs: list[str]) -> list[dict[str, Any]]:
    """Record the bytes actually published by a successful job."""
    return [{"path": str(path), "bytes": Path(path).stat().st_size,
             "sha256": _sha256(Path(path))} for path in outputs]


def _verify_sources(record: dict[str, Any]) -> None:
    trace = record.get("provider_trace", [])
    if not trace:
        raise ResumeError(f"success has no verifiable input provenance: {record['job_id']}")
    for item in trace:
        reference = item.get("source_reference") or {}
        fingerprint = reference.get("fingerprint")
        path = reference.get("path")
        if not path or not isinstance(fingerprint, list) or len(fingerprint) != 5:
            raise ResumeError(f"success lacks a local source fingerprint: {record['job_id']}")
        stat = Path(path).stat()
        current = [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]
        if current != fingerprint:
            raise ResumeError(f"input changed since checkpoint: {path}")


def resume_records(path: Path, identity: dict[str, Any], expected_outputs: dict[str, Path],
                   job_ids: list[str]) -> tuple[dict[str, dict[str, Any]], int]:
    """Preflight every reused record before the caller writes any checkpoint."""
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(previous, dict):
            raise ResumeError("checkpoint must be a JSON object")
        if previous.get("checkpoint_format") != 1:
            raise ResumeError("resume requires a checkpoint from the current runner")
        if previous.get("recovery_identity") != identity:
            raise ResumeError("task, compiled plan, resources or software changed since checkpoint")
        records = previous.get("results", [])
        if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
            raise ResumeError("checkpoint results must be a job list")
        if [row.get("job_id") for row in records] != job_ids:
            raise ResumeError("checkpoint job order does not match the current plan")
        reused = {}
        for record in records:
            if record.get("status") != "success":
                continue
            job_id = record["job_id"]
            expected = expected_outputs.get(job_id)
            if expected is None or record.get("outputs") != [str(expected)]:
                raise ResumeError(f"checkpoint output paths do not match the plan: {job_id}")
            if record.get("outputs_info") != output_information(record["outputs"]):
                raise ResumeError(f"output changed since checkpoint: {job_id}")
            _verify_sources(record)
            reused[job_id] = {**record, "reused": True}
        return reused, int(previous.get("attempt", 1)) + 1
    except (OSError, ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, ResumeError):
            raise
        raise ResumeError(f"cannot verify resume checkpoint: {exc}") from exc
