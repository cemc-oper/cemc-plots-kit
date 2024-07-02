from pathlib import Path
from typing import Union

import pandas as pd


def get_local_file_path(
        grib2_dir: Union[str, Path],
        grib2_file_name_template: str,
        start_time: pd.Timestamp,
        forecast_time: pd.Timedelta
) -> Path:
    start_time_label = start_time.strftime("%Y%m%d%H")
    forecast_hour = int(forecast_time / pd.Timedelta(hours=1))
    forecat_hour_label = f"{forecast_hour:03d}"
    file_name = grib2_file_name_template.format(
        start_time_label=start_time_label,
        forecast_hour_label=forecat_hour_label
    )
    file_path = Path(grib2_dir, file_name)
    return file_path
