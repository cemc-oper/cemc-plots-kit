from pathlib import Path
from dataclasses import dataclass

import pandas as pd


from cedarkit.maps.util import AreaRange


@dataclass
class CommonConfig:
    source_grib2_dir: Path
    work_dir: Path
    system_name: str
    area: AreaRange
    grib2_file_name_template: str = "rmf.hgra.{start_time_label}{forecast_hour_label}.grb2"


@dataclass
class TimeConfig:
    start_time: pd.Timestamp
    forecast_time: pd.Timedelta


@dataclass
class PlotConfig:
    plot_name: str


@dataclass
class JobConfig:
    common_config: CommonConfig
    time_config: TimeConfig
    plot_config: PlotConfig
