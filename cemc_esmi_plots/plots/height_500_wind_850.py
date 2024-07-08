from copy import deepcopy

import numpy as np

from cedarkit.comp.smooth import smth9
from cedarkit.comp.util import apply_to_xarray_values

from cedarkit.maps.chart import Panel

from cemc_plot_kit.plots.cn.height_500_wind_850.default import PlotData, PlotMetadata, plot
from cemc_plot_kit.data.field_info import hgt_info, u_info, v_info
from cemc_plot_kit.data.source import get_field_from_file

from cemc_esmi_plots.source import get_local_file_path
from cemc_esmi_plots.config import PlotConfig, TimeConfig, ExprConfig, JobConfig
from cemc_esmi_plots.logger import get_logger


# set_default_map_loader_package("cedarkit.maps.map.cemc")

PLOT_NAME = "height_500_wind_850"

plot_logger = get_logger(PLOT_NAME)


def load_data(expr_config: ExprConfig, time_config: TimeConfig) -> PlotData:
    # system -> data file
    grib2_dir = expr_config.source_grib2_dir
    grib2_file_name_template = expr_config.grib2_file_name_template
    start_time = time_config.start_time
    forecast_time = time_config.forecast_time

    file_path = get_local_file_path(
        grib2_dir=grib2_dir,
        grib2_file_name_template=grib2_file_name_template,
        start_time=start_time,
        forecast_time=forecast_time
    )
    plot_logger.info(f"get local file path: {file_path}")

    # data file -> data field
    plot_logger.info("loading height 500hPa...")
    hgt_500_info = deepcopy(hgt_info)
    hgt_500_info.level_type = "pl"
    hgt_500_info.level = 500
    h_500_field = get_field_from_file(field_info=hgt_500_info, file_path=file_path)

    plot_logger.info("loading u 850hPa...")
    u_850_info = deepcopy(u_info)
    u_850_info.level_type = "pl"
    u_850_info.level = 850
    u_850_field = get_field_from_file(
        field_info=u_850_info,
        file_path=file_path,
    )

    plot_logger.info("loading v 850hPa...")
    v_850_info = deepcopy(v_info)
    v_850_info.level_type = "pl"
    v_850_info.level = 850
    v_850_field = get_field_from_file(
        field_info=v_850_info,
        file_path=file_path,
    )

    # data field -> plot data
    plot_logger.info("calculating...")
    # 单位转换
    h_500_field = h_500_field / 10.
    # 平滑
    h_500_field = apply_to_xarray_values(h_500_field, lambda x: smth9(x, 0.5, 0.25, False))
    h_500_field = apply_to_xarray_values(h_500_field, lambda x: smth9(x, 0.5, 0.25, False))

    wind_speed_850_field = (np.sqrt(u_850_field * u_850_field + v_850_field * v_850_field))

    return PlotData(
        hgt_500_field=h_500_field,
        u_850_field=u_850_field,
        v_850_field=v_850_field,
        wind_speed_850_field=wind_speed_850_field,
    )


def run_plot(job_config: JobConfig) -> Panel:
    expr_config = job_config.expr_config
    time_config = job_config.time_config
    plot_config = job_config.plot_config

    system_name = expr_config.system_name
    start_time = time_config.start_time
    forecast_time = time_config.forecast_time

    metadata = PlotMetadata(
        start_time=start_time,
        forecast_time=forecast_time,
        system_name=system_name,
        area_range=expr_config.area,
    )

    plot_logger.info("loading data...")
    plot_data = load_data(
        expr_config=expr_config,
        time_config=time_config,
    )
    plot_logger.info("loading data...done")

    # field -> plot
    plot_logger.info("plotting...")
    panel = plot(
        plot_data=plot_data,
        plot_metadata=metadata,
    )
    plot_logger.info("plotting...done")

    del plot_data

    # plot -> output
    return panel
