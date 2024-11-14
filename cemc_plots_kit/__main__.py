from pathlib import Path

import typer
import pandas as pd

from cedarkit.maps.util import AreaRange

from cemc_plots_kit.task import run_task
from cemc_plots_kit.draw import draw_plot
from cemc_plots_kit.config import parse_start_time


app = typer.Typer()


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
