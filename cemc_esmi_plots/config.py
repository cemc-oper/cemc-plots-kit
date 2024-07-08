from pathlib import Path
from dataclasses import dataclass

import pandas as pd


from cedarkit.maps.util import AreaRange


@dataclass
class ExprConfig:
    """
    试验参数，对于整个试验都保持不变的信息
    """
    system_name: str
    area: AreaRange
    source_grib2_dir: Path
    grib2_file_name_template: str = "rmf.hgra.{start_time_label}{forecast_hour_label}.grb2"


@dataclass
class RuntimeConfig:
    """
    运行参数
    """
    work_dir: Path


@dataclass
class TimeConfig:
    """
    时间参数，用于绘制不同时次、时效的图片
    """
    start_time: pd.Timestamp
    forecast_time: pd.Timedelta


@dataclass
class PlotConfig:
    """
    绘图参数，定义绘图需要的定制参数，每类绘图一个对象
    """
    plot_name: str


@dataclass
class JobConfig:
    """
    单次绘图作业的配置信息
    """
    expr_config: ExprConfig
    time_config: TimeConfig
    runtime_config: RuntimeConfig
    plot_config: PlotConfig


def parse_start_time(start_time_str: str) -> pd.Timestamp:
    """
    解析起报时间

    Parameters
    ----------
    start_time_str
        格式：
        * YYYYMMDDHHMM
        * YYYYMMDDHH

    Returns
    -------
    pd.Timestamp
    """
    if len(start_time_str) == 12:
        format_str = "%Y%m%d%H%M"
    elif len(start_time_str) == 10:
        format_str = "%Y%m%d%H%"
    elif len(start_time_str) == 8:
        format_str = "%Y%m%d"
    else:
        raise ValueError(f"start time string is not supported: {start_time_str}")
    return pd.to_datetime(start_time_str, format=format_str)
