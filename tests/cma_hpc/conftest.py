import sys
import os

import pytest
import pandas as pd
from loguru import logger

from cedarkit.maps.util import AreaRange


logger.remove()
logger.add(sys.stderr, level="WARNING")


@pytest.fixture
def root_work_dir():
    job_dir = os.environ["JOBDIR"]
    return f"{job_dir}/workspace/cedarkit/cemc_esmi_plots/tests/cma_hpc"


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


@pytest.fixture
def area_north_china() -> AreaRange:
    return AreaRange.from_tuple((105, 125, 34, 45))
