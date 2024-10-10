from pathlib import Path
import shutil

import pytest
import pandas as pd

from cedarkit.maps.util import AreaRange
from cemc_esmi_plots.draw import draw_plot


@pytest.fixture
def base_work_dir(root_work_dir):
    return f"{root_work_dir}/api/draw"


def test_draw_plot(cma_gfs_system_name, last_two_day, forecast_time_24h, cma_gfs_data_dir, base_work_dir):
    system_name = cma_gfs_system_name
    plot_type = "height_500_mslp"
    start_time = last_two_day
    forecast_time = forecast_time_24h
    data_dir = cma_gfs_data_dir
    work_dir = f"{base_work_dir}/{system_name}/{plot_type}"
    data_file_name_template = "gmf.gra.{start_time_label}{forecast_hour_label}.grb2"

    start_time_label = start_time.strftime("%Y%m%d%H")
    forecast_hour_label = f"{int(forecast_time / pd.Timedelta(hours=1)):03d}"
    image_name = f"{plot_type}_{start_time_label}_{forecast_hour_label}.png"
    image_file_path = Path(work_dir, image_name)

    shutil.rmtree(work_dir, ignore_errors=True)

    draw_plot(
        system_name=system_name,
        plot_type=plot_type,
        start_time=start_time,
        forecast_time=forecast_time,
        data_dir=data_dir,
        work_dir=work_dir,
        data_file_name_template=data_file_name_template,
    )

    assert image_file_path.exists()
