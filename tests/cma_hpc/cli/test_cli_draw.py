import os
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner


from cemc_esmi_plots.__main__ import app


@pytest.fixture
def runner():
    runner = CliRunner()
    return runner


@pytest.fixture
def base_work_dir():
    return "/g7/JOB_TMP/wangdp/workspace/cedarkit/cemc_esmi_plots/tests/cma_hpc/cli/draw"


def test_draw_height_500_mslp(runner, cma_gfs_system_name, last_two_day, forecast_time_24h, cma_gfs_data_dir, base_work_dir):
    system_name = cma_gfs_system_name
    plot_type = "height_500_mslp"
    start_time = last_two_day
    start_time_str = start_time.strftime("%Y%m%d%H")  # 2024100900
    forecast_time = forecast_time_24h
    forecast_time_str = f"{int(forecast_time / pd.Timedelta(hours=1))}h"  # 24h
    data_dir = cma_gfs_data_dir
    work_dir = base_work_dir

    start_time_label = start_time_str
    forecast_time_label = f"{int(pd.to_timedelta(forecast_time_str) / pd.Timedelta(hours=1)):03d}"  # 024
    image_file_path = Path(work_dir, f"{plot_type}_{start_time_label}_{forecast_time_label}.png")

    if image_file_path.exists():
        os.remove(image_file_path)

    result = runner.invoke(app, [
        "draw",
        "--system-name", system_name,
        "--plot-type", plot_type,
        "--start-time", start_time_str,
        "--forecast-time", forecast_time_str,
        "--data-dir", data_dir,
        "--work-dir", work_dir,
        # "--data-file-name-template", "gmf.gra.{start_time_label}{forecast_hour_label}.grb2",
    ])

    assert result.exit_code == 0
    assert image_file_path.exists()
