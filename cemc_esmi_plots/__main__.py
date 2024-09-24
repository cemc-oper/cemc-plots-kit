from pathlib import Path

import typer

from cemc_esmi_plots.task import run_task


app = typer.Typer()


@app.command()
def task(task_file: Path = typer.Option()):
    run_task(task_file_path=task_file)


@app.command()
def draw(
        system_name: str = typer.Option(),
        plot_type: str = typer.Option(),
        start_time: str = typer.Option(),
        forecast_time: str = typer.Option(),
        data_dir = typer.Option(),
        work_dir = typer.Option(),
        **kwargs,
):
    ...


if __name__ == "__main__":
    app()
