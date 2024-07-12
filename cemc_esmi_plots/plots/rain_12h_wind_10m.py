import pandas as pd

from cedarkit.maps.chart import Panel

from cemc_plot_kit.data import DataLoader
from cemc_plot_kit.plots.cn.rain_wind_10m.default import PlotData, PlotMetadata, plot, load_data

from cemc_esmi_plots.source import EsmiLocalDataSource
from cemc_esmi_plots.config import PlotConfig, TimeConfig, ExprConfig, JobConfig
from cemc_esmi_plots.logger import get_logger


# set_default_map_loader_package("cedarkit.maps.map.cemc")

PLOT_NAME = "rain_12h_wind_10m"

plot_logger = get_logger(PLOT_NAME)


def load(expr_config: ExprConfig, time_config: TimeConfig) -> PlotData:
    # system -> data file
    start_time = time_config.start_time
    forecast_time = time_config.forecast_time

    data_source = EsmiLocalDataSource(expr_config=expr_config)
    data_loader = DataLoader(data_source=data_source)

    plot_data = load_data(
        data_loader=data_loader,
        start_time=start_time,
        forecast_time=forecast_time,
        interval=pd.Timedelta(hours=12),
    )
    return plot_data


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
        interval=pd.Timedelta(hours=12)
    )

    plot_logger.info("loading data...")
    plot_data = load(
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


def check_available(time_config: TimeConfig, plot_config: PlotConfig) -> bool:
    return time_config.forecast_time >= pd.Timedelta(hours=12)
