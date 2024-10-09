import shutil

import pytest
import pandas as pd

from cemc_esmi_plots.job import run_job
from cemc_esmi_plots.config import JobConfig, ExprConfig, RuntimeConfig, TimeConfig, PlotConfig



@pytest.fixture
def base_work_dir():
    return "/g7/JOB_TMP/wangdp/workspace/cedarkit/cemc_esmi_plots/tests/cma_hpc/api/job"


def test_run_job(cma_gfs_system_name, last_two_day, forecast_time_24h, cma_gfs_data_dir, base_work_dir):
    system_name = cma_gfs_system_name
    start_time = last_two_day
    forecast_time = forecast_time_24h
    data_dir = cma_gfs_data_dir
    case_base_work_dir = base_work_dir
    plot_type = "height_500_mslp"

    job_config = JobConfig(
        expr_config=ExprConfig(
            data_dir=data_dir,
            system_name=system_name,
            data_file_name_template="gmf.gra.{start_time_label}{forecast_hour_label}.grb2"
        ),
        runtime_config=RuntimeConfig(
            base_work_dir=case_base_work_dir,
        ),
        time_config=TimeConfig(
            start_time=start_time,
            forecast_time=forecast_time,
        ),
        plot_config=PlotConfig(
            plot_name=plot_type,
        )
    )

    shutil.rmtree(case_base_work_dir, ignore_errors=True)

    output_file_list = run_job(job_config)
    assert len(output_file_list) == 1
    output_file = output_file_list[0]

    start_time_label = start_time.strftime("%Y%m%d%H")
    forecast_time_label = f"{int(forecast_time/pd.Timedelta(hours=1)):03d}"
    assert (
        str(output_file.absolute()) ==
        f"{base_work_dir}/output/{plot_type}_{start_time_label}_{forecast_time_label}.png"
    )
    assert output_file_list[0].exists()
