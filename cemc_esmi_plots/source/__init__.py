from pathlib import Path
from typing import Union

import pandas as pd


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
