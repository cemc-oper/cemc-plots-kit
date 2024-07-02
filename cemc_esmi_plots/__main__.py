from pathlib import Path

import typer

from cemc_esmi_plots.task import run_task


app = typer.Typer()


@app.command()
def run(task_file: Path = typer.Option()):
    run_task(task_file_path=task_file)


if __name__ == "__main__":
    app()
