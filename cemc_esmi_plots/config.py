from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Union

import pandas as pd


from cedarkit.maps.util import AreaRange


@dataclass
class ExprConfig:
    """
    试验参数，对于整个试验都保持不变的信息
    """
    system_name: str
    data_dir: Union[str, Path]
    area: Optional[AreaRange] = None
    data_file_name_template: Optional[str] = "rmf.hgra.{start_time_label}{forecast_hour_label}.grb2"


@dataclass
class RuntimeConfig:
    """
    运行参数，每类绘图一个对象
    """
    base_work_dir: Optional[Union[str, Path]] = None
    work_dir: Optional[Union[str, Path]]  = None
    output_dir: Optional[Union[str, Path]]  = None


@dataclass
class TimeConfig:
    """
    时间参数，用于绘制不同时次、时效的图片，每个绘图一个对象
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
    单次绘图作业的配置信息，包括

    * 试验配置
    * 时间参数
    * 运行时参数
    * 绘图参数
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
        起报时次字符串，支持格式：

        * YYYYMMDDHHMM: 年月日时分
        * YYYYMMDDHH: 年月日时

    Returns
    -------
    pd.Timestamp
        解析后的时间对象

    Examples
    --------
    年月日时分

    >>> parse_start_time("202409230000")
    Timestamp('2024-09-23 00:00:00')

    年月日时

    >>> parse_start_time("2024092300")
    Timestamp('2024-09-23 00:00:00')

    年月日

    >>> parse_start_time("20240923")
    Timestamp('2024-09-23 00:00:00')

    """
    if len(start_time_str) == 12:
        format_str = "%Y%m%d%H%M"
    elif len(start_time_str) == 10:
        format_str = "%Y%m%d%H"
    elif len(start_time_str) == 8:
        format_str = "%Y%m%d"
    else:
        raise ValueError(f"start time string is not supported: {start_time_str}")
    return pd.to_datetime(start_time_str, format=format_str)


def get_default_data_file_name_template(system_name: str) -> Optional[str]:
    """
    返回默认数据文件名模板

    Parameters
    ----------
    system_name
        系统名称

    Returns
    -------
    Optional[str]
        数据文件名模板，如果不识别系统名则返回 None
    """
    system_name = system_name.lower()
    system_name = system_name.replace("-", "_")
    if system_name in ["cma_gfs", "cma_gfs_gmf"]:
        return "gmf.gra.{start_time_label}{forecast_hour_label}.grb2"
    elif system_name in ["cma_meso","cma_meso_3km", "cma_meso_1km"]:
        return "rmf.hgra.{start_time_label}{forecast_hour_label}.grb2"
    elif system_name in ["cma_tym"]:
        return "rmf.tcgra.{start_time_label}{forecast_hour_label}.grb2"
    else:
        return None


def get_default_data_dir(system_name: str) -> Optional[str]:
    """
    返回默认数据路径，默认数据存放在 CMA-HPC2023-A。

    Parameters
    ----------
    system_name
        系统名称

    Returns
    -------
    Optional[str]
        数据路径，如果不识别系统名称则返回 None
    """
    system_name = system_name.lower()
    system_name = system_name.replace("-", "_")
    if system_name in ["cma_gfs", "cma_gfs_gmf"]:
        return "/g3/COMMONDATA/OPER/CEMC/GFS_GMF/Prod-grib/{start_time_label}/ORIG"
    elif system_name in ["cma_meso","cma_meso_3km", "cma_meso_1km"]:
        return "/g3/COMMONDATA/OPER/CEMC/MESO_3KM/Prod-grib/{start_time_label}/ORIG"
    elif system_name in ["cma_meso_1km"]:
        return "/g3/COMMONDATA/OPER/CEMC/MESO_1KM/Prod-grib/{start_time_label}/ORIG"
    elif system_name in ["cma_tym"]:
        return "/g3/COMMONDATA/OPER/CEMC/TYM/Prod-grib/{start_time_label}/ORIG"
    else:
        return None
