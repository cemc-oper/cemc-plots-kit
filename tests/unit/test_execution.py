import json

import pytest
import reki

from cemc_plots_kit.execution import run_task_spec
from cemc_plots_kit.task_spec import load_task_spec


TASK = """\
api_version: cemc.plots/v2
kind: PlotTask
source:
  dataset: cma_gfs_gmf_cmadaas_mount
  overrides: {storage_base: /CMADAAS}
time: {start_time: 2026071600, forecast_time: 24h, forecast_interval: 24h}
runtime: {work_dir: work, output_dir: output, missing: skip}
plots: {cn.t2m: true}
"""


def test_serial_run_writes_atomic_manifest(tmp_path, monkeypatch):
    path = tmp_path / "task.yaml"
    path.write_text(TASK, encoding="utf-8")

    def fake_run_job(config, **kwargs):
        output = config.runtime_config.output_dir / (config.plot_config.plot_name.replace(".", "_") + ".png")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"png")
        return [output]

    monkeypatch.setattr("cemc_plots_kit.execution.run_job", fake_run_job)
    result = run_task_spec(load_task_spec(path), task_file=path)

    manifest = tmp_path / "output/task-manifest.json"
    assert result["status"] == "success"
    assert manifest.exists()
    assert json.loads(manifest.read_text())["task_plan_identity"] == result["task_plan_identity"]
    assert not list(manifest.parent.glob(".*.tmp"))


def test_missing_field_is_skipped_and_recorded(tmp_path, monkeypatch):
    path = tmp_path / "task.yaml"
    path.write_text(TASK, encoding="utf-8")
    monkeypatch.setattr(
        "cemc_plots_kit.execution.run_job",
        lambda config, **kwargs: (_ for _ in ()).throw(reki.DataNotFoundError(reki.FieldQuery(parameter="t2m"))),
    )
    result = run_task_spec(load_task_spec(path), task_file=path)
    assert result["status"] == "partial"
    assert {item["reason"] for item in result["results"]} == {"field_missing"}


def test_shared_reads_reuses_one_provider_and_can_be_disabled(tmp_path, monkeypatch):
    path = tmp_path / "task.yaml"
    path.write_text(TASK, encoding="utf-8")
    providers = []

    def fake_run_job(config, *, data_source=None):
        providers.append(data_source)
        return []

    monkeypatch.setattr("cemc_plots_kit.execution.run_job", fake_run_job)
    shared = run_task_spec(load_task_spec(path), task_file=path)
    assert len(providers) == 2
    assert providers[0] is providers[1]
    assert shared["sharing"]["shared_reads"] is True

    providers.clear()
    path.write_text(TASK.replace("missing: skip", "missing: skip, shared_reads: false"), encoding="utf-8")
    unshared = run_task_spec(load_task_spec(path), task_file=path)
    assert providers == [None, None]
    assert unshared["sharing"]["shared_reads"] is False
