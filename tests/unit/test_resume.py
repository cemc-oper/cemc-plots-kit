import json
import signal
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cemc_plots_kit import __main__ as cli
from cemc_plots_kit import execution, run_state
from cemc_plots_kit.execution import TaskExecutionError, TaskInterrupted, run_task_spec
from cemc_plots_kit.job import get_output_image_file_name
from cemc_plots_kit.task_spec import load_task_spec


TASK = """\
api_version: cemc.plots/v2
kind: PlotTask
source:
  dataset: cma_gfs_gmf_cmadaas_mount
  overrides: {storage_base: /CMADAAS}
time: {start_time: 2026110212, forecast_start: 6h, forecast_time: 18h, forecast_interval: 6h}
runtime: {work_dir: work, output_dir: output, missing: fail}
plots: {cn.t2m: {style_variant: cn_summer}}
"""


@pytest.fixture
def local_run(tmp_path, monkeypatch):
    task_file = tmp_path / "task.yaml"
    task_file.write_text(TASK)
    source_file = tmp_path / "input.grib2"
    source_file.write_bytes(b"frozen test input")
    providers = []

    class Provider:
        cache_info = {"hits": 0, "misses": 0, "entries": 0}

        def __init__(self, *args, **kwargs):
            self.closed = False
            providers.append(self)

        def close(self):
            self.closed = True

    monkeypatch.setattr(execution, "RekiProvider", Provider)
    calls = []
    interrupt = {"enabled": True}

    def run_job(config, *, data_source=None, evidence=None):
        hours = int(config.time_config.forecast_time.total_seconds() / 3600)
        calls.append(hours)
        manifest = json.loads((tmp_path / "output/task-manifest.json").read_text())
        assert manifest["status"] == "running"
        assert manifest["results"][hours // 6 - 1]["status"] == "running"
        stat = source_file.stat()
        evidence["provider_trace"] = [{"source_reference": {
            "path": str(source_file),
            "fingerprint": [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns],
        }}]
        evidence["timings"] = {"total_seconds": 0.1}
        if hours == 12 and interrupt["enabled"]:
            raise KeyboardInterrupt()
        output = config.runtime_config.output_dir / get_output_image_file_name(config)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(f"complete output {hours}".encode())
        return [output]

    monkeypatch.setattr(execution, "run_job", run_job)
    return task_file, source_file, providers, calls, interrupt


def _interrupt(task_file):
    with pytest.raises(KeyboardInterrupt):
        run_task_spec(load_task_spec(task_file), task_file=task_file)
    path = task_file.parent / "output/task-manifest.json"
    return path, json.loads(path.read_text())


def test_interrupt_checkpoints_completed_active_and_pending_jobs(local_run):
    task_file, _, providers, calls, _ = local_run
    path, document = _interrupt(task_file)
    assert calls == [6, 12]
    assert document["status"] == "interrupted"
    assert [row["status"] for row in document["results"]] == ["success", "interrupted", "not_run"]
    assert document["results"][0]["outputs_info"][0]["sha256"]
    assert document["results"][1]["provider_trace"]
    assert document["results"][1]["timings"] == {"total_seconds": 0.1}
    assert document["interruption"]["signal"] == "SIGINT"
    assert all(provider.closed for provider in providers)
    assert not list(path.parent.glob(".*.tmp*"))


def test_resume_reuses_verified_success_and_retries_remaining_jobs(local_run):
    task_file, _, providers, calls, interrupt = local_run
    _, before = _interrupt(task_file)
    first = Path(before["results"][0]["outputs"][0])
    before_stat = first.stat()
    calls.clear()
    interrupt["enabled"] = False
    result = run_task_spec(load_task_spec(task_file), task_file=task_file, resume=True)
    assert result["status"] == "success"
    assert result["attempt"] == 2
    assert calls == [12, 18]
    assert result["results"][0]["reused"] is True
    assert result["recovery"]["reused_job_ids"] == [before["results"][0]["job_id"]]
    after_stat = first.stat()
    assert (after_stat.st_ino, after_stat.st_size, after_stat.st_mtime_ns, after_stat.st_ctime_ns) == (
        before_stat.st_ino, before_stat.st_size, before_stat.st_mtime_ns, before_stat.st_ctime_ns)
    assert all(provider.closed for provider in providers)


@pytest.mark.parametrize("change", ["input", "output", "missing_output", "software", "dependency", "task_bytes", "definitions", "unproven_input"])
def test_resume_rejects_changes_before_mutating_checkpoint(local_run, monkeypatch, change):
    task_file, source_file, _, calls, interrupt = local_run
    path, document = _interrupt(task_file)
    if change == "input":
        source_file.write_bytes(b"a new input generation")
    elif change == "output":
        Path(document["results"][0]["outputs"][0]).write_bytes(b"corrupt output")
    elif change == "missing_output":
        Path(document["results"][0]["outputs"][0]).unlink()
    elif change == "software":
        version = run_state.version
        monkeypatch.setattr(run_state, "version", lambda name: version(name) + ".changed")
    elif change == "dependency":
        versions = run_state.installed_versions()
        monkeypatch.setattr(run_state, "installed_versions", lambda: {**versions, "numpy": "changed"})
    elif change == "task_bytes":
        task_file.write_text(task_file.read_text() + "\n# changed source document\n")
    elif change == "definitions":
        document["recovery_identity"]["definitions"] = [{"sha256": "different"}]
        path.write_text(json.dumps(document))
    elif change == "unproven_input":
        document["results"][0]["provider_trace"] = []
        path.write_text(json.dumps(document))
    previous = path.read_bytes()
    calls.clear()
    interrupt["enabled"] = False
    with pytest.raises(TaskExecutionError, match="resume rejected"):
        run_task_spec(load_task_spec(task_file), task_file=task_file, resume=True)
    assert path.read_bytes() == previous
    assert calls == []


def test_resume_rejects_changed_external_recipe_before_writing(local_run):
    task_file, _, _, calls, interrupt = local_run
    recipe = task_file.parent / "custom.yaml"
    example = Path(__file__).resolve().parents[2] / "examples/recipes/t2m_custom.yaml"
    recipe.write_text(example.read_text())
    task_file.write_text(TASK.replace("cn.t2m:", "custom.yaml:"))
    path, _ = _interrupt(task_file)
    previous = path.read_bytes()
    recipe.write_text(recipe.read_text().replace("Custom 2m Temperature", "Changed 2m Temperature"))
    calls.clear()
    interrupt["enabled"] = False
    with pytest.raises(TaskExecutionError, match="resume rejected"):
        run_task_spec(load_task_spec(task_file), task_file=task_file, resume=True)
    assert path.read_bytes() == previous
    assert calls == []


def test_default_run_repeats_all_jobs_instead_of_implicitly_resuming(local_run):
    task_file, _, _, calls, interrupt = local_run
    _interrupt(task_file)
    calls.clear()
    interrupt["enabled"] = False
    result = run_task_spec(load_task_spec(task_file), task_file=task_file)
    assert calls == [6, 12, 18]
    assert result["attempt"] == 1
    assert result["recovery"]["resumed"] is False


@pytest.mark.parametrize("checkpoint", [None, {"api_version": "cemc.plots.manifest/v1", "results": []}])
def test_resume_requires_current_checkpoint(local_run, checkpoint):
    task_file, _, _, calls, _ = local_run
    path = task_file.parent / "output/task-manifest.json"
    if checkpoint is not None:
        path.parent.mkdir()
        path.write_text(json.dumps(checkpoint))
    with pytest.raises(TaskExecutionError, match="resume rejected"):
        run_task_spec(load_task_spec(task_file), task_file=task_file, resume=True)
    assert calls == []
    assert path.exists() == (checkpoint is not None)


def test_resume_rejects_multiple_workers_before_writing(local_run):
    task_file, _, _, calls, _ = local_run
    task_file.write_text(TASK.replace("missing: fail", "missing: fail, workers: 2"))
    with pytest.raises(TaskExecutionError, match="workers=1"):
        run_task_spec(load_task_spec(task_file), task_file=task_file, resume=True)
    assert calls == []
    assert not (task_file.parent / "output").exists()


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, lambda: TaskInterrupted("SIGTERM")])
def test_cli_interrupt_returns_130_and_restores_sigterm_handler(tmp_path, monkeypatch, interruption):
    path = tmp_path / "task.yaml"
    path.write_text(TASK)
    previous = signal.getsignal(signal.SIGTERM)

    def interrupted(*args, **kwargs):
        assert signal.getsignal(signal.SIGTERM) is not previous
        raise interruption()

    monkeypatch.setattr(cli, "run_task_spec", interrupted)
    result = CliRunner().invoke(cli.app, ["run", str(path)])
    assert result.exit_code == 130
    assert "task_interrupted" in result.output
    assert signal.getsignal(signal.SIGTERM) is previous


def test_cli_sigterm_handler_raises_task_interrupted_and_restores():
    previous = signal.getsignal(signal.SIGTERM)
    with pytest.raises(TaskInterrupted) as error:
        with cli._termination_interrupt():
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
    assert error.value.signal_name == "SIGTERM"
    assert signal.getsignal(signal.SIGTERM) is previous
