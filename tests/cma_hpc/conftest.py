import sys
import os
from dataclasses import dataclass
from typing import Optional

import pytest
import pandas as pd
from loguru import logger

from cedarkit.maps.util import AreaRange


logger.remove()
logger.add(sys.stderr, level="WARNING")


@pytest.fixture
def root_work_dir():
    job_dir = os.environ["JOBDIR"]
    return f"{job_dir}/workspace/cedarkit/cemc_plots_kit/tests/cma_hpc"


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


@pytest.fixture
def cma_gfs_data_dir():
    return "/g3/COMMONDATA/OPER/CEMC/GFS_GMF/Prod-grib/{start_time_label}/ORIG"


@dataclass
class PlotArea:
    name: str
    area: AreaRange
    level: float


cn_areas = [
    PlotArea(name="NorthEast", area=AreaRange.from_tuple((108, 137, 37, 55)), level=850),
    PlotArea(name="NorthChina", area=AreaRange.from_tuple((105, 125, 34, 45)), level=850),
    PlotArea(name="EastChina", area=AreaRange.from_tuple((105, 130, 28, 40)), level=850),
    PlotArea(name="SouthChina", area=AreaRange.from_tuple((103, 128, 15, 32)), level=850),
    PlotArea(name="East_NorthWest", area=AreaRange.from_tuple((85, 115, 30, 45)), level=700),
    PlotArea(name="East_SouthWest", area=AreaRange.from_tuple((95, 113, 20, 35)), level=700),
    PlotArea(name="XinJiang", area=AreaRange.from_tuple((70, 100, 33, 50)), level=700),
    PlotArea(name="XiZang", area=AreaRange.from_tuple((75, 105, 25, 40)), level=500),
    PlotArea(name="CentralChina", area=AreaRange.from_tuple((95, 120, 25, 40)), level=850),
]


def get_plot_area(name: str) -> Optional[PlotArea]:
    for plot_area in cn_areas:
        if plot_area.name == name:
            return plot_area
    return None


@pytest.fixture
def cn_area_north_china() -> PlotArea:
    return get_plot_area("NorthChina")
