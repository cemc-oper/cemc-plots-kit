from pathlib import Path

import pytest
import pandas as pd

from cedarkit.maps.util import AreaRange
from cemc_esmi_plots.draw import draw_plot


@pytest.fixture
def cma_gfs_system_name() -> str:
    return "CMA-GFS"


@pytest.fixture
def last_two_day() -> pd.Timestamp:
    current = pd.Timestamp.now().floor(freq="D")
    last_two_day = current - pd.Timedelta(days=2)
    return last_two_day


@pytest.fixture
def forecast_time_24h() -> pd.Timedelta:
    return pd.to_timedelta("24h")


def test_draw_plot(cma_gfs_system_name, last_two_day, forecast_time_24h):
    draw_plot(
        system_name=cma_gfs_system_name,
        plot_type="height_500_mslp",
        start_time=last_two_day,
        forecast_time=forecast_time_24h,
        data_dir=Path("/g3/COMMONDATA/OPER/CEMC/GFS_GMF/Prod-grib/{start_time_label}/ORIG"),
        work_dir=Path("/g7/JOB_TMP/wangdp/workspace/cedarkit/cemc_esmi_plots/tests/cma_hpc"),
        data_file_name_template="gmf.gra.{start_time_label}{forecast_hour_label}.grb2",
        area=None,
    )


