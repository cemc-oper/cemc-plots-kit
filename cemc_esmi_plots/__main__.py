from pathlib import Path

import typer
import pandas as pd

from cemc_esmi_plots.task import run_task
from cemc_esmi_plots.draw import draw_plot
from cemc_esmi_plots.config import parse_start_time


app = typer.Typer()


@app.command()
def task(task_file: Path = typer.Option()):
    run_task(task_file_path=task_file)


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
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
):
    start_time = parse_start_time(start_time)
    forecast_time = pd.to_timedelta(forecast_time)
    draw_plot(
        system_name=system_name,
        plot_type=plot_type,
        start_time=start_time,
        forecast_time=forecast_time,
        data_dir=data_dir,
        data_file_name_template=data_file_name_template,
        work_dir=work_dir,
    )


if __name__ == "__main__":
    app()
