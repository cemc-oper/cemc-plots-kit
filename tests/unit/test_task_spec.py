import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cemc_plots_kit.__main__ import app
from cemc_plots_kit.task_spec import (
    PlotTaskV2,
    TaskSpecError,
    convert_v1_task,
    load_task_spec,
    mounted_catalog_path,
    resolve_task_source,
)


V2_TASK = """\
api_version: cemc.plots/v2
kind: PlotTask
source:
  dataset: cma_gfs_gmf_cmadaas_mount
  overrides: {storage_base: /CMADAAS}
time:
  start_time: 2026071600
  forecast_time: 24h
  forecast_interval: 6h
plots: {cn.t2m: true}
"""


def test_v2_task_normalizes_duration_and_resolves_local_mount(tmp_path):
    path = tmp_path / "task.yaml"
    path.write_text(V2_TASK, encoding="utf-8")
    task = load_task_spec(path)
    assert task.time.start_time == "202607160000"
    assert task.time.forecast_time == "1 days 00:00:00"
    source = resolve_task_source(task.source)
    assert source.name == "local"
    assert source.kwargs == {"data_class": "cmadaas", "storage_base": "/CMADAAS"}


def test_remote_dataset_fails_policy_before_provider_io(tmp_path):
    path = tmp_path / "task.yaml"
    path.write_text(V2_TASK.replace("cma_gfs_gmf_cmadaas_mount", "CMA-GFS-CMADaaS"), encoding="utf-8")
    with pytest.raises(TaskSpecError, match="source policy"):
        load_task_spec(path)


def test_unknown_fields_are_rejected(tmp_path):
    path = tmp_path / "task.yaml"
    path.write_text(V2_TASK + "unexpected: true\n", encoding="utf-8")
    with pytest.raises(TaskSpecError, match="extra_forbidden"):
        load_task_spec(path)


def test_v1_conversion_is_pure_and_keeps_plot_forms():
    legacy = {
        "system_name": "CMA-GFS",
        "time": {"start_time": "2026071600", "forecast_time": "24h", "forecast_interval": "6h"},
        "runtime": {"base_work_dir": "run"},
        "plots": {"cn.t2m": True, "cn.rain_wind_10m": [{"interval": "6h"}]},
    }
    converted = convert_v1_task(legacy)
    assert legacy["runtime"] == {"base_work_dir": "run"}
    assert converted["plots"] == legacy["plots"]
    assert PlotTaskV2.model_validate({key: value for key, value in converted.items() if key != "_legacy_source"})


def test_packaged_schema_has_no_drift():
    packaged = json.loads((Path(__file__).parents[2] / "src/cemc_plots_kit/schemas/task-v2.json").read_text())
    assert packaged == PlotTaskV2.model_json_schema()


def test_catalog_example_has_no_machine_mount_path():
    assert "/CMADAAS" not in mounted_catalog_path().read_text(encoding="utf-8")


def test_validate_cli_returns_stable_failure_code(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("api_version: cemc.plots/v9\n", encoding="utf-8")
    result = CliRunner().invoke(app, ["validate", str(path)])
    assert result.exit_code == 2
    assert "validation" in result.output.lower() or "missing" in result.output.lower()
