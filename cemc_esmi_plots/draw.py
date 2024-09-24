from pathlib import Path
from typing import Optional

import pandas as pd

from cedarkit.maps.util import AreaRange
from cemc_esmi_plots.config import JobConfig, ExprConfig, RuntimeConfig, TimeConfig, PlotConfig
from cemc_esmi_plots.job import run_job


def draw_plot(
        system_name: str,
        plot_type: str,
        start_time: pd.Timestamp,
        forecast_time: pd.Timedelta,
        data_dir: Path,
        work_dir: Path,
        data_file_name_template: str = None,
        area: Optional[AreaRange] = None,
):
    job_config = JobConfig(
        expr_config=ExprConfig(
            system_name=system_name,
            area=area,
            source_grib2_dir=data_dir,
            grib2_file_name_template=data_file_name_template,

        ),
        runtime_config=RuntimeConfig(
            work_dir=work_dir,
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
