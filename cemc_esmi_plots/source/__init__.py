from pathlib import Path
from typing import Union

import pandas as pd
import xarray as xr

from cedar_graph.data import DataSource, FieldInfo
from cedar_graph.data.source import get_field_from_file

from cemc_esmi_plots.config import ExprConfig


class ExprLocalDataSource(DataSource):
    """
    模式试验本地数据源。模式 GRIB2 产品文件归档需要满足以下要求：

    * 本地文件系统，支持 POSIX 协议
    * 单个时次的 GRIB2 数据保存在同一个目录中
    * GRIB2 文件名模板支持特定变量，参见 ``get_local_file_path`` 函数文档

    Attributes
    ----------
    expr_config : ExprConfig
        试验配置信息，包括

        * `grib2_dir`: GRIB2 数据目录
        * `grib2_file_name_template`: GRIB2 数据文件名模板
    """
    def __init__(self, expr_config: ExprConfig):
        super().__init__()
        self.expr_config = expr_config

    def retrieve(
            self, field_info: FieldInfo, start_time: pd.Timestamp, forecast_time: pd.Timedelta
    ) -> xr.DataArray or None:
        """
        从本地 GRIB2 文件中加载要素场

        Parameters
        ----------
        field_info
            要素信息
        start_time
            起报时次
        forecast_time
            预报时效

        Returns
        -------
        xr.DataArray or None
            返回检索到的要素场，如果没找到则返回 None
        """
        # system -> data file
        grib2_dir = self.expr_config.source_grib2_dir
        grib2_file_name_template = self.expr_config.grib2_file_name_template

        file_path = get_local_file_path(
            grib2_dir=grib2_dir,
            grib2_file_name_template=grib2_file_name_template,
            start_time=start_time,
            forecast_time=forecast_time
        )

        # data file -> data field
        field = get_field_from_file(field_info=field_info, file_path=file_path)
        return field



def get_local_file_path(
        grib2_dir: Union[str, Path],
        grib2_file_name_template: str,
        start_time: pd.Timestamp,
        forecast_time: pd.Timedelta,
) -> Path:
    """
    返回拼接的本地 GRIB2 文件路径

    Parameters
    ----------
    grib2_dir
        GRIB2 目录，单个时次的所有 GRIB2 数据都保存在同一个目录中
    grib2_file_name_template
        GRIB2 文件模板，可以包含如下格式化字符串
            * start_time_label：起报时间，YYYYMMDDHH
            * forecast_hour_label：预报时效，小时，FFF
        文件名示例如下：
            * CMA-GFS: gmf.gra.{start_time_label}{forecast_hour_label}.grb2
            * CMA-MESO: rmf.hgra.{start_time_label}{forecast_hour_label}.grb2
    start_time
        起报时间
    forecast_time
        预报时效

    Returns
    -------
    Path
        本地 GRIB2 文件路径

    Examples
    --------
    >>> get_local_file_path(
    ...     grib2_dir="/grib2/dir",
    ...     grib2_file_name_template="rmf.hgra.{start_time_label}{forecast_hour_label}.grb2",
    ...     start_time=pd.to_datetime("2023-09-23 00:00"),
    ...     forecast_time=pd.to_timedelta("24h"),
    ... )
    PosixPath('/grib2/dir/rmf.hgra.2023092300024.grb2')

    """
    start_time_label = start_time.strftime("%Y%m%d%H")
    forecast_hour = int(forecast_time / pd.Timedelta(hours=1))
    forecat_hour_label = f"{forecast_hour:03d}"
    file_name = grib2_file_name_template.format(
        start_time_label=start_time_label,
        forecast_hour_label=forecat_hour_label
    )
    file_path = Path(grib2_dir, file_name)
    return file_path
