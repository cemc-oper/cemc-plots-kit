from cedarkit.maps.chart import Panel

from cemc_plot_kit.plots.cn.t_2m.default import PlotData, PlotMetadata, plot
from cemc_plot_kit.data.field_info import t_2m_info, FieldInfo
from cemc_plot_kit.data.source import get_field_from_file

from cemc_esmi_plots.source import get_local_file_path
from cemc_esmi_plots.config import PlotConfig, TimeConfig, CommonConfig, JobConfig
from cemc_esmi_plots.logger import get_logger

# set_default_map_loader_package("cedarkit.maps.map.cemc")

PLOT_NAME = "t_2m"

plot_logger = get_logger(PLOT_NAME)


def load_data(common_config: CommonConfig, time_config: TimeConfig) -> PlotData:
    # system -> data file
    grib2_dir = common_config.source_grib2_dir
    grib2_file_name_template = common_config.grib2_file_name_template
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
    t_2m_field = get_field_from_file(field_info=t_2m_info, file_path=file_path)

    # data field -> plot data
    t_2m_field = t_2m_field - 273.15

    return PlotData(
        t_2m_field=t_2m_field
    )


def run_plot(job_config: JobConfig) -> Panel:
    common_config = job_config.common_config
    time_config = job_config.time_config
    plot_config = job_config.plot_config

    system_name = common_config.system_name
    start_time = time_config.start_time
    forecast_time = time_config.forecast_time

    metadata = PlotMetadata(
        start_time=start_time,
        forecast_time=forecast_time,
        system_name=system_name,
        area_range=common_config.area,
    )

    plot_logger.info("loading data...")
    plot_data = load_data(
        common_config=common_config,
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

    return panel
