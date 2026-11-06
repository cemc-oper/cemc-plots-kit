from pathlib import Path
from contextlib import contextmanager
import json
import signal

import typer

from cemc_plots_kit.task_spec import TaskSpecError, load_task_spec
from cemc_plots_kit.task_plan import TaskPlanError, build_task_plan, explain_task_plan
from cemc_plots_kit.execution import TaskExecutionError, TaskInterrupted, run_task_spec


app = typer.Typer()


@app.command(help="validate a versioned task without reading data or rendering plots.")
def validate(task_file: Path = typer.Argument(..., exists=True, dir_okay=False)):
    try:
        task_spec = load_task_spec(task_file)
    except TaskSpecError as exc:
        typer.echo(json.dumps({"valid": False, "code": "task_validation", "message": str(exc)}), err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps({
        "valid": True,
        "api_version": task_spec.api_version,
        "kind": task_spec.kind,
        "dataset": task_spec.source.dataset,
    }, sort_keys=True))


def _load_plan(task_file: Path):
    return build_task_plan(load_task_spec(task_file), task_file=task_file)


@app.command(help="compile a task into a static plan without reading field values.")
def plan(task_file: Path = typer.Argument(..., exists=True, dir_okay=False)):
    try:
        typer.echo(_load_plan(task_file).to_json(pretty=True))
    except (TaskSpecError, TaskPlanError) as exc:
        typer.echo(json.dumps({"valid": False, "code": "task_plan", "message": str(exc)}), err=True)
        raise typer.Exit(code=2) from exc


@app.command(help="explain one planned plot/time combination.")
def explain(
    task_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    plot: str = typer.Option(..., "--plot"),
    forecast_time: str = typer.Option(..., "--forecast-time"),
):
    try:
        typer.echo(json.dumps(explain_task_plan(_load_plan(task_file), plot=plot, forecast_time=forecast_time), indent=2, sort_keys=True))
    except (TaskSpecError, TaskPlanError) as exc:
        typer.echo(json.dumps({"valid": False, "code": "task_explain", "message": str(exc)}), err=True)
        raise typer.Exit(code=2) from exc


@contextmanager
def _termination_interrupt():
    """Let CLI SIGTERM use the same checkpoint and cleanup path as Ctrl-C."""
    def interrupt(signum, frame):
        raise TaskInterrupted(signal.Signals(signum).name)

    previous = signal.signal(signal.SIGTERM, interrupt)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


@app.command(help="execute a versioned task, optionally resuming verified completed jobs.")
def run(task_file: Path = typer.Argument(..., exists=True, dir_okay=False),
        resume: bool = typer.Option(False, "--resume", help="Reuse verified successful jobs from a checkpoint (workers=1).")):
    try:
        with _termination_interrupt():
            result = run_task_spec(load_task_spec(task_file), task_file=task_file, resume=resume)
    except KeyboardInterrupt as exc:
        typer.echo(json.dumps({"valid": False, "code": "task_interrupted",
                               "signal": getattr(exc, "signal_name", "SIGINT")}), err=True)
        raise typer.Exit(code=130) from exc
    except (TaskSpecError, TaskPlanError, TaskExecutionError) as exc:
        typer.echo(json.dumps({"valid": False, "code": "task_run", "message": str(exc)}), err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    app()
