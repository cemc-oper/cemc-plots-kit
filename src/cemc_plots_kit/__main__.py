from pathlib import Path
import json

import typer

from cemc_plots_kit.task_spec import TaskSpecError, load_task_spec
from cemc_plots_kit.task_plan import TaskPlanError, build_task_plan, explain_task_plan
from cemc_plots_kit.execution import run_task_spec


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


@app.command(help="execute a versioned task with one deterministic worker.")
def run(task_file: Path = typer.Argument(..., exists=True, dir_okay=False)):
    try:
        result = run_task_spec(load_task_spec(task_file), task_file=task_file)
    except (TaskSpecError, TaskPlanError) as exc:
        typer.echo(json.dumps({"valid": False, "code": "task_run", "message": str(exc)}), err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    app()
