from pathlib import Path
from typing import Optional, Union

import pandas as pd

from cedarkit.plots.types import AreaRange
from cemc_plots_kit.config import (
    JobConfig, RuntimeConfig, TimeConfig, PlotConfig,
)
from cemc_plots_kit.job import run_job
from cemc_plots_kit.task import bind_task_source


def draw_plot(
        system_name: str,
        plot_type: str,
        start_time: pd.Timestamp,
        forecast_time: pd.Timedelta,
        work_dir: Union[str, Path] = None,
        data_dir: Union[str, Path] = None,
        data_file_name_template: Optional[str] = None,
        area: Optional[AreaRange] = None,
) -> list[Path]:
    """
    Draw a figure and save in working directory

    Parameters
    ----------
    system_name
        system name
    plot_type
        type of plot
    start_time
    forecast_time
    work_dir
        working directory
    data_dir
        data directory
    data_file_name_template
        data file name template
    area
        plot area, default is CN.

    Returns
    -------
    list[Path]
        path list of generated figures
    """
    if work_dir is None:
        work_dir = "."

    source_config = {}
    if data_dir is not None:
        source_config["data_dir"] = data_dir
    if data_file_name_template is not None:
        source_config["data_file_name_template"] = data_file_name_template

    job_config = JobConfig(
        expr_config=bind_task_source(system_name, source_config, Path.cwd(), area),
        runtime_config=RuntimeConfig(
            work_dir=work_dir,
            output_dir=work_dir,
        ),
        time_config=TimeConfig(
            start_time=start_time,
            forecast_time=forecast_time
        ),
        plot_config=PlotConfig(
            plot_name=plot_type,
        )
    )

    outputs = run_job(job_config)
    return outputs
