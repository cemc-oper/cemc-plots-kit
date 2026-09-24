"""Deterministic task execution, including isolated process workers."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from time import time
from typing import Any

import pandas as pd
import reki
from cedar_graph.data import RekiProvider
from cedarkit.plots.types import AreaRange

from cemc_plots_kit.config import ExprConfig, JobConfig, PlotConfig, RuntimeConfig, TimeConfig
from cemc_plots_kit.errors import classify_error
from cemc_plots_kit.job import get_output_image_file_name, run_job
from cemc_plots_kit.manifest import write_manifest
from cemc_plots_kit.task_plan import TaskPlan, build_task_plan
from cemc_plots_kit.task_spec import PlotTaskV2, resolve_task_dataset


class TaskExecutionError(RuntimeError):
    """A worker failed after its serializable failure was recorded."""


class ExecutionContext:
    """Provider resources owned by exactly one serial task execution."""

    def __init__(self, source, *, shared_reads: bool, region=None):
        self.shared_reads = shared_reads
        self.provider = RekiProvider(source.source, region=region) if shared_reads else None

    def provider_for_job(self):
        return self.provider

    def summary(self) -> dict[str, Any]:
        cache = self.provider.cache_info if self.provider is not None else {"hits": 0, "misses": 0, "entries": 0}
        return {"shared_reads": self.shared_reads, "field_cache": dict(cache)}

    def close(self):
        if self.provider is not None:
            self.provider.close()


def _job_config(job: dict[str, Any], task: PlotTaskV2, plan: TaskPlan, source) -> JobConfig:
    runtime = plan.document["runtime"]
    area = task.area.model_dump() if task.area is not None else None
    return JobConfig(
        expr_config=ExprConfig(source_spec=source.source,
                               dataset_id=source.record.dataset_id,
                               area=AreaRange(**area) if area is not None else None),
        runtime_config=RuntimeConfig(work_dir=Path(runtime["work_dir"]), output_dir=Path(runtime["output_dir"])),
        time_config=TimeConfig(start_time=pd.Timestamp(task.time.start_time), forecast_time=pd.Timedelta(job["forecast_time"])),
        plot_config=PlotConfig(plot_name=job["plot"], plot_params=job["params"], base_dir=Path(plan.document["task"]["file"]).parent),
    )


def _run_group(group: list[tuple[int, str, JobConfig]], provider, storage_base: str | None) -> list[tuple[int, dict[str, Any]]]:
    """Run a group against its already-owned provider."""
    results: list[tuple[int, dict[str, Any]]] = []
    for index, job_id, config in group:
        try:
            outputs = run_job(config, data_source=provider)
        except Exception as exc:
            results.append((index, {"job_id": job_id, "status": "error", "is_missing": isinstance(exc, reki.DataNotFoundError), "code": classify_error(exc, storage_base=storage_base), "type": type(exc).__name__, "message": str(exc)}))
            break
        results.append((index, {"job_id": job_id, "status": "success", "outputs": [str(path) for path in outputs]}))
    return results


def _run_worker_group(group: list[tuple[int, str, JobConfig]], source_spec, shared_reads: bool,
                      storage_base: str | None, region=None) -> list[tuple[int, dict[str, Any]]]:
    """Run one group in a child process, rebuilding all reader-owned state."""
    provider = RekiProvider(source_spec, region=region) if shared_reads else None
    try:
        return _run_group(group, provider, storage_base)
    finally:
        if provider is not None:
            provider.close()


def _worker_groups(jobs: list[tuple[int, dict[str, Any], JobConfig]]) -> list[list[tuple[int, str, JobConfig]]]:
    """Make stable one-job groups while physical file identity is unresolved."""
    return [[(index, job["id"], config)] for index, job, config in jobs]


def _check_output_collisions(jobs: list[tuple[int, dict[str, Any], JobConfig]]) -> None:
    seen: dict[Path, str] = {}
    for _, job, config in jobs:
        output = Path(config.runtime_config.output_dir) / get_output_image_file_name(config)
        previous = seen.setdefault(output, job["id"])
        if previous != job["id"]:
            raise TaskExecutionError(f"output collision: {previous} and {job['id']} both write {output}")


def _result_from_worker(item: dict[str, Any], missing: str) -> tuple[dict[str, Any], bool]:
    if item["status"] == "success":
        return {"job_id": item["job_id"], "status": "success", "outputs": item["outputs"]}, False
    if item["is_missing"] and missing in {"skip", "warn"}:
        return {"job_id": item["job_id"], "status": "skipped", "reason": item["code"], "warning": missing == "warn"}, False
    return {"job_id": item["job_id"], "status": "failed", "error": {key: item[key] for key in ("code", "type", "message")}}, True


def run_task_spec(task: PlotTaskV2, *, task_file: Path) -> dict[str, Any]:
    """Run a v2 task, using isolated processes only when workers exceeds one."""
    plan = build_task_plan(task, task_file=task_file)
    source = resolve_task_dataset(task.source)
    started = time()
    executable = [(index, job, _job_config(job, task, plan, source)) for index, job in enumerate(plan.document["jobs"]) if job["executable"]]
    _check_output_collisions(executable)
    by_index: dict[int, dict[str, Any]] = {}
    fatal = False

    if task.runtime.workers == 1:
        region = task.area.model_dump() if task.area is not None else None
        context = ExecutionContext(source, shared_reads=task.runtime.shared_reads, region=region)
        try:
            for index, job, config in executable:
                record, failed = _result_from_worker(_run_group([(index, job["id"], config)], context.provider_for_job(), source.source.kwargs.get("storage_base"))[0][1], task.runtime.missing)
                by_index[index] = record
                if failed:
                    fatal = True
            sharing = context.summary()
        finally:
            context.close()
    else:
        groups = _worker_groups(executable)
        if groups:
            with ProcessPoolExecutor(max_workers=min(task.runtime.workers, len(groups)), mp_context=get_context("spawn")) as pool:
                region = task.area.model_dump() if task.area is not None else None
                futures = [pool.submit(_run_worker_group, group, source.source, task.runtime.shared_reads,
                                       source.source.kwargs.get("storage_base"), region) for group in groups]
                try:
                    for group, future in zip(groups, futures):
                        try:
                            items = future.result()
                        except Exception as exc:
                            index, job_id, _ = group[0]
                            by_index[index] = {
                                "job_id": job_id,
                                "status": "failed",
                                "error": {"code": "worker_crash", "type": type(exc).__name__, "message": str(exc)},
                            }
                            fatal = True
                            continue
                        for index, item in items:
                            record, failed = _result_from_worker(item, task.runtime.missing)
                            by_index[index] = record
                            fatal = fatal or failed
                except KeyboardInterrupt:
                    for future in futures:
                        future.cancel()
                    raise
        sharing = {"shared_reads": task.runtime.shared_reads, "field_cache": {"hits": 0, "misses": 0, "entries": 0}, "worker_groups": len(groups)}

    results: list[dict[str, Any]] = []
    for index, job in enumerate(plan.document["jobs"]):
        if not job["executable"]:
            results.append({"job_id": job["id"], "status": "skipped", "reason": job.get("skip_reason", job["issues"][0] if job["issues"] else "not_executable")})
        elif index in by_index:
            results.append(by_index[index])
        else:
            results.append({"job_id": job["id"], "status": "not_run", "reason": "previous_job_failed"})

    status = "failed" if fatal else ("partial" if any(item["status"] == "skipped" for item in results) else "success")
    document = {"api_version": "cemc.plots.manifest/v1", "task_plan_identity": plan.identity, "status": status, "duration_seconds": time() - started, "source": {"dataset_id": source.record.dataset_id, "catalog_origin": source.origin, "provider": source.source.name}, "sharing": sharing, "results": results}
    manifest_path = Path(plan.document["runtime"]["output_dir"]) / "task-manifest.json"
    document["manifest_path"] = str(write_manifest(manifest_path, document))
    if fatal:
        first = next(item for item in results if item["status"] == "failed")
        raise TaskExecutionError(f"{first['error']['code']}: {first['error']['message']}")
    return document
