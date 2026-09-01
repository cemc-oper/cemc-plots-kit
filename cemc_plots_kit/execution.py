"""Deterministic single-worker execution and manifest publication."""

from __future__ import annotations

from pathlib import Path
from time import time
from typing import Any

import pandas as pd
import reki
from cedar_graph.data import RekiProvider

from cemc_plots_kit.config import ExprConfig, JobConfig, PlotConfig, RuntimeConfig, TimeConfig
from cemc_plots_kit.errors import classify_error
from cemc_plots_kit.job import run_job
from cemc_plots_kit.manifest import write_manifest
from cemc_plots_kit.task_plan import TaskPlan, build_task_plan
from cemc_plots_kit.task_spec import PlotTaskV2, resolve_task_dataset


class ExecutionContext:
    """Provider resources owned by exactly one serial task execution."""

    def __init__(self, source, *, shared_reads: bool):
        self.shared_reads = shared_reads
        self.provider = RekiProvider(source.source) if shared_reads else None

    def provider_for_job(self):
        return self.provider

    def summary(self) -> dict[str, Any]:
        cache = self.provider.cache_info if self.provider is not None else {"hits": 0, "misses": 0, "entries": 0}
        return {"shared_reads": self.shared_reads, "field_cache": dict(cache)}

    def close(self):
        if self.provider is not None:
            self.provider._field_cache.clear()


def _job_config(job: dict[str, Any], task: PlotTaskV2, plan: TaskPlan, source) -> JobConfig:
    runtime = plan.document["runtime"]
    return JobConfig(
        expr_config=ExprConfig(system_name=source.record.dataset_id, data_dir="", source_spec=source.source, dataset_id=source.record.dataset_id),
        runtime_config=RuntimeConfig(work_dir=Path(runtime["work_dir"]), output_dir=Path(runtime["output_dir"])),
        time_config=TimeConfig(start_time=pd.Timestamp(task.time.start_time), forecast_time=pd.Timedelta(job["forecast_time"])),
        plot_config=PlotConfig(plot_name=job["plot"], plot_params=job["params"], base_dir=Path(plan.document["task"]["file"]).parent),
    )


def run_task_spec(task: PlotTaskV2, *, task_file: Path) -> dict[str, Any]:
    """Run a v2 task serially; output publication is represented even on failure."""
    plan = build_task_plan(task, task_file=task_file)
    source = resolve_task_dataset(task.source)
    context = ExecutionContext(source, shared_reads=task.runtime.shared_reads)
    results: list[dict[str, Any]] = []
    fatal: Exception | None = None
    started = time()
    for job in plan.document["jobs"]:
        if not job["executable"]:
            results.append({"job_id": job["id"], "status": "skipped", "reason": job.get("skip_reason", job["issues"][0] if job["issues"] else "not_executable")})
            continue
        try:
            outputs = run_job(_job_config(job, task, plan, source), data_source=context.provider_for_job())
        except Exception as exc:
            code = classify_error(exc, storage_base=source.source.kwargs.get("storage_base"))
            is_missing = isinstance(exc, reki.DataNotFoundError)
            if is_missing and task.runtime.missing in {"skip", "warn"}:
                results.append({"job_id": job["id"], "status": "skipped", "reason": code, "warning": task.runtime.missing == "warn"})
                continue
            results.append({"job_id": job["id"], "status": "failed", "error": {"code": code, "type": type(exc).__name__, "message": str(exc)}})
            fatal = exc
            break
        results.append({"job_id": job["id"], "status": "success", "outputs": [str(path) for path in outputs]})

    status = "failed" if fatal else ("partial" if any(item["status"] == "skipped" for item in results) else "success")
    document = {
        "api_version": "cemc.plots.manifest/v1",
        "task_plan_identity": plan.identity,
        "status": status,
        "duration_seconds": time() - started,
        "source": {"dataset_id": source.record.dataset_id, "catalog_origin": source.origin, "provider": source.source.name},
        "sharing": context.summary(),
        "results": results,
    }
    manifest_path = Path(plan.document["runtime"]["output_dir"]) / "task-manifest.json"
    document["manifest_path"] = str(write_manifest(manifest_path, document))
    context.close()
    if fatal:
        raise fatal
    return document
