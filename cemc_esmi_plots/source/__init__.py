from pathlib import Path
from typing import Union

import pandas as pd
import xarray as xr

from cemc_plot_kit.data import DataSource, FieldInfo
from cemc_plot_kit.data.source import get_field_from_file

from cemc_esmi_plots.config import ExprConfig


class EsmiLocalDataSource(DataSource):
    """
    科创平台本地数据源

    Attributes
    ----------
    expr_config: ExprConfig
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
        start_time
        forecast_time

        Returns
        -------
        xr.DataArray or None
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
    start_time
        起报时间
    forecast_time
        预报时效

    Returns
    -------
    Path
        本地 GRIB2 文件路径
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
