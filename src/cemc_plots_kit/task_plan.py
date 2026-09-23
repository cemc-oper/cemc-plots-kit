"""Static, JSON-serializable planning for versioned plot tasks."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from cemc_plots_kit.config import PlotConfig, TimeConfig
from cemc_plots_kit.plots import (EnsembleRequest, EnsembleT2MProduct, WorkflowProduct,
                                  check_plot_available, get_plot_definition, workflow_context)
from cemc_plots_kit.task import parse_plots_config
from cemc_plots_kit.task_spec import PlotTaskV2, resolve_task_dataset


class TaskPlanError(ValueError):
    """A task cannot be statically planned."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _identity(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class TaskPlan:
    """A runtime-free plan: dictionaries only, never readers, arrays or figures."""

    document: dict[str, Any]

    @property
    def identity(self) -> str:
        return self.document["identity"]

    def to_dict(self) -> dict[str, Any]:
        return self.document

    def to_json(self, *, pretty: bool = False) -> str:
        return json.dumps(self.document, sort_keys=True, indent=2 if pretty else None)


def _request_identity(request: dict[str, Any]) -> str:
    request = dict(request)
    request.pop("provider_slot", None)
    return _canonical(request)


def build_task_plan(task: PlotTaskV2, *, task_file: Path) -> TaskPlan:
    """Compile recipes and requests without constructing a provider or decoding data."""
    task_file = Path(task_file).resolve()
    source = resolve_task_dataset(task.source)
    base_dir = task_file.parent
    start_time = pd.Timestamp(task.time.start_time)
    forecast_times = pd.timedelta_range(
        "0h", pd.Timedelta(task.time.forecast_time), freq=pd.Timedelta(task.time.forecast_interval),
    )
    jobs: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    grouped_requests: dict[str, dict[str, Any]] = {}

    for forecast_time in forecast_times:
        for plot_name, params in parse_plots_config(task.plots):
            job_id = f"{plot_name}:{forecast_time.isoformat()}:{_identity(params)[:12]}"
            try:
                definition = get_plot_definition(plot_name, base_dir=base_dir)
                available = check_plot_available(
                    definition,
                    time_config=TimeConfig(start_time=start_time, forecast_time=forecast_time),
                    plot_config=PlotConfig(plot_name=plot_name, plot_params=params, base_dir=base_dir),
                )
            except Exception as exc:
                issues.append({"code": "recipe_error", "job_id": job_id, "message": str(exc)})
                jobs.append({"id": job_id, "plot": plot_name, "params": params, "forecast_time": str(forecast_time), "executable": False, "issues": ["recipe_error"]})
                continue
            if not available:
                jobs.append({"id": job_id, "plot": plot_name, "params": params, "forecast_time": str(forecast_time), "executable": False, "skip_reason": "plot_unavailable_for_time", "issues": []})
                continue
            try:
                if isinstance(definition, EnsembleT2MProduct):
                    request = EnsembleRequest.from_params(params)
                    member_plans = definition.compile_members(
                        start_time=start_time, forecast_time=forecast_time, request=request)
                    plot_plan = {"product": definition.name, "member_plans": {
                        member_id: member_plan.to_dict() for member_id, member_plan in member_plans.items()},
                        "max_input_ids": list(request.member_ids) + (
                            [request.control_id] if request.include_control_in_max else []),
                        "missing_policy": request.missing_policy}
                    plans_to_group = [(member_id, member_plan.to_dict())
                                      for member_id, member_plan in member_plans.items()]
                elif isinstance(definition, WorkflowProduct):
                    plot_plan = definition.compile(workflow_context(
                        TimeConfig(start_time=start_time, forecast_time=forecast_time),
                        PlotConfig(plot_name=plot_name, plot_params=params, base_dir=base_dir))).to_dict()
                    plans_to_group = [(None, plot_plan)]
                else:
                    raise TypeError(f"plot {plot_name!r} has no v3 product plan")
            except Exception as exc:
                issues.append({"code": "plan_compile_error", "job_id": job_id, "message": str(exc)})
                jobs.append({"id": job_id, "plot": plot_name, "params": params, "forecast_time": str(forecast_time), "executable": False, "issues": ["plan_compile_error"]})
                continue
            jobs.append({"id": job_id, "plot": plot_name, "params": params, "forecast_time": str(forecast_time), "executable": True, "issues": [], "plot_plan": plot_plan, "physical_file": {"status": "resolve_on_execute"}})
            for member_id, member_plan in plans_to_group:
                for node in member_plan["nodes"]:
                    request = node.get("request")
                    if request is None:
                        continue
                    key = _request_identity(request)
                    entry = grouped_requests.setdefault(key, {"request": request, "consumers": []})
                    consumer = {"job_id": job_id, "node_id": node["id"], "bindings": node["bindings"]}
                    if member_id is not None:
                        consumer["member_id"] = member_id
                    entry["consumers"].append(consumer)

    normalized_input = task.model_dump(mode="json")
    document = {
        "api_version": "cemc.plots.task-plan/v1",
        "identity": _identity({"task": normalized_input, "task_file": task_file.name}),
        "task": {"file": str(task_file), "normalized": normalized_input},
        "source": {"dataset_id": source.record.dataset_id, "catalog_origin": source.origin, "source_spec": repr(source.source)},
        "runtime": {"work_dir": str((base_dir / task.runtime.work_dir).resolve()) if not task.runtime.work_dir.is_absolute() else str(task.runtime.work_dir), "output_dir": str((base_dir / task.runtime.output_dir).resolve()) if not task.runtime.output_dir.is_absolute() else str(task.runtime.output_dir), "workers": task.runtime.workers},
        "jobs": jobs,
        "requests": [grouped_requests[key] for key in sorted(grouped_requests)],
        "worker_groups": [{"id": "local:unresolved", "job_ids": [job["id"] for job in jobs if job["executable"]], "reason": "physical files resolve during execute"}],
        "issues": issues,
        "environment_observations": [],
    }
    return TaskPlan(document)


def explain_task_plan(plan: TaskPlan, *, plot: str, forecast_time: str) -> dict[str, Any]:
    """Return one stable job explanation without observing a data source."""
    target = pd.Timedelta(forecast_time)
    for job in plan.document["jobs"]:
        if job["plot"] == plot and pd.Timedelta(job["forecast_time"]) == target:
            requests = [request for request in plan.document["requests"] if any(item["job_id"] == job["id"] for item in request["consumers"])]
            return {"task_plan_identity": plan.identity, "job": job, "requests": requests}
    raise TaskPlanError(f"no planned job for plot={plot!r}, forecast_time={forecast_time!r}")
