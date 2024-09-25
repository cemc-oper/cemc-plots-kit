from pathlib import Path
from typing import Optional, Union

import pandas as pd

from cedarkit.maps.util import AreaRange
from cemc_esmi_plots.config import (
    JobConfig, ExprConfig, RuntimeConfig, TimeConfig, PlotConfig,
    get_default_data_file_name_template, get_default_data_dir
)
from cemc_esmi_plots.job import run_job


def draw_plot(
        system_name: str,
        plot_type: str,
        start_time: pd.Timestamp,
        forecast_time: pd.Timedelta,
        work_dir: Union[str, Path] = None,
        data_dir: Union[str, Path] = None,
        data_file_name_template: Optional[str] = None,
        area: Optional[AreaRange] = None,
):
    if data_file_name_template is None:
        data_file_name_template = get_default_data_file_name_template(system_name=system_name)
    if data_file_name_template is None:
        raise ValueError(f"can't get default data_file_name_template with system_name {system_name}")

    if data_dir is None:
        data_dir = get_default_data_dir(system_name=system_name)
    if data_dir is None:
        raise ValueError(f"can't get default data_dir with system_name {system_name}")

    if work_dir is None:
        work_dir = "."

    job_config = JobConfig(
        expr_config=ExprConfig(
            system_name=system_name,
            area=area,
            data_dir=data_dir,
            data_file_name_template=data_file_name_template,
        ),
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

    run_job(job_config)
