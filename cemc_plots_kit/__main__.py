from pathlib import Path
import json

import typer
import pandas as pd

from cedarkit.plots.types import AreaRange

from cemc_plots_kit.task import run_task
from cemc_plots_kit.task_spec import TaskSpecError, load_task_spec
from cemc_plots_kit.task_plan import TaskPlanError, build_task_plan, explain_task_plan
from cemc_plots_kit.draw import draw_plot
from cemc_plots_kit.config import parse_start_time


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


@app.command(
    help="draw multiple plots using a task file.",
)
def task(task_file: Path = typer.Option(..., help="task file path.")):
    run_task(task_file_path=task_file)


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    help="draw a plot",
)
def draw(
        ctx: typer.Context,
        system_name: str = typer.Option(),
        plot_type: str = typer.Option(),
        start_time: str = typer.Option(),
        forecast_time: str = typer.Option(),
        data_dir = typer.Option(None),
        data_file_name_template = typer.Option(None),
        work_dir = typer.Option(None),
        area = typer.Option(None, help="plot area, default is CN, format: start_longitude,end_longitude,start_latitude,end_latitude"),
):
    start_time = parse_start_time(start_time)
    forecast_time = pd.to_timedelta(forecast_time)

    if area is not None:
        area_tokens = area.split(',')
        if len(area_tokens) != 4:
            raise ValueError(f"Invalid area {area}, area format is start_longitude,end_longitude,start_latitude,end_latitude")
        area_tokens_float = [float(i) for i in area_tokens]
        area = AreaRange.from_tuple(area_tokens_float)

    draw_plot(
        system_name=system_name,
        plot_type=plot_type,
        start_time=start_time,
        forecast_time=forecast_time,
        data_dir=data_dir,
        data_file_name_template=data_file_name_template,
        work_dir=work_dir,
        area=area,
    )


if __name__ == "__main__":
    app()
