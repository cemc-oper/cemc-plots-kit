import json

import reki
import pytest
from typer.testing import CliRunner

from cemc_plots_kit.__main__ import app
from cemc_plots_kit.task_plan import build_task_plan, explain_task_plan
from cemc_plots_kit.task_spec import load_task_spec


TASK = """\
api_version: cemc.plots/v2
kind: PlotTask
source:
  dataset: cma_gfs_gmf_cmadaas_mount
  overrides: {storage_base: /CMADAAS}
time: {start_time: 2026071600, forecast_time: 24h, forecast_interval: 24h}
plots: {cn.t2m: true, cn.h_500_psl: true, cn.rain_24h: true}
"""


def test_build_task_plan_is_static_and_deduplicates_requests(tmp_path, monkeypatch):
    task_file = tmp_path / "task.yaml"
    task_file.write_text(TASK, encoding="utf-8")
    monkeypatch.setattr(reki, "from_source", lambda *args, **kwargs: pytest.fail("plan opened a source"))

    plan = build_task_plan(load_task_spec(task_file), task_file=task_file)
    document = plan.to_dict()

    assert document["api_version"] == "cemc.plots.task-plan/v1"
    assert document["source"]["dataset_id"] == "cma_gfs_gmf_cmadaas_mount"
    assert document["environment_observations"] == []
    assert all(job["physical_file"]["status"] == "resolve_on_execute" for job in document["jobs"] if job["executable"])
    assert any(job["skip_reason"] == "plot_unavailable_for_time" for job in document["jobs"] if not job["executable"])
    assert all(request["consumers"] for request in document["requests"])


def test_explain_returns_one_job_and_its_requests(tmp_path):
    task_file = tmp_path / "task.yaml"
    task_file.write_text(TASK, encoding="utf-8")
    plan = build_task_plan(load_task_spec(task_file), task_file=task_file)
    result = explain_task_plan(plan, plot="cn.t2m", forecast_time="24h")
    assert result["job"]["executable"] is True
    assert result["requests"]


def test_plan_and_explain_cli_emit_json(tmp_path):
    task_file = tmp_path / "task.yaml"
    task_file.write_text(TASK, encoding="utf-8")
    runner = CliRunner()
    plan = runner.invoke(app, ["plan", str(task_file)])
    assert plan.exit_code == 0
    assert json.loads(plan.output)["jobs"]
    explain = runner.invoke(app, ["explain", str(task_file), "--plot", "cn.t2m", "--forecast-time", "24h"])
    assert explain.exit_code == 0
    assert json.loads(explain.output)["job"]["plot"] == "cn.t2m"
