from pathlib import Path
import shutil

import pytest
import pandas as pd

from cedarkit.maps.util import AreaRange
from cemc_esmi_plots.draw import draw_plot


def test_draw_plot(cma_gfs_system_name, last_two_day, forecast_time_24h, cma_gfs_data_dir):
    data_dir = cma_gfs_data_dir
    work_dir = "/g7/JOB_TMP/wangdp/workspace/cedarkit/cemc_esmi_plots/tests/cma_hpc/api/draw"
    plot_type = "height_500_mslp"
    start_time = last_two_day
    forecast_time = forecast_time_24h

    shutil.rmtree(work_dir, ignore_errors=True)

    draw_plot(
        system_name=cma_gfs_system_name,
        plot_type=plot_type,
        start_time=start_time,
        forecast_time=forecast_time,
        data_dir=data_dir,
        work_dir=work_dir,
        data_file_name_template="gmf.gra.{start_time_label}{forecast_hour_label}.grb2",
    )

    start_time_label = start_time.strftime("%Y%m%d%H")
    forecast_hour_label = f"{int(forecast_time / pd.Timedelta(hours=1)):03d}"
    image_name = f"{plot_type}_{start_time_label}_{forecast_hour_label}.png"
    assert Path(work_dir, image_name).exists()
