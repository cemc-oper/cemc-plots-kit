from cedarkit.maps.chart import Panel

from cedar_graph.data import DataLoader
from cedar_graph.plots.cn.height_500_mslp.default import PlotData, PlotMetadata, plot, load_data

from cemc_plots_kit.source import ExprLocalDataSource
from cemc_plots_kit.config import PlotConfig, TimeConfig, ExprConfig, JobConfig
from cemc_plots_kit.logger import get_logger


# set_default_map_loader_package("cedarkit.maps.map.cemc")
PLOT_NAME = "height_500_mslp"
plot_logger = get_logger(PLOT_NAME)


def run_plot(job_config: JobConfig) -> Panel:
    """
    Plot a figure using job configuration (``job_config``).

    Parameters
    ----------
    job_config
        job configuration

    Returns
    -------
    Panel
        plot panel object
    """
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
    plot_data = _load(
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
    """
    Check if the current image can be plotted with the time combination.
    For example, the 24-hour precipitation forecast requires a forecast lead time of at least 24 hours.

    Parameters
    ----------
    time_config
    plot_config

    Returns
    -------
    bool
        whether it is possible to plot
    """
    return True


def _load(expr_config: ExprConfig, time_config: TimeConfig) -> PlotData:
    """
    Load required fields for plotting from data.

    Parameters
    ----------
    expr_config
        experiment configuration which is used to create ``ExprLocalDataSource``
    time_config
        time configuration

    Returns
    -------
    PlotData
        required fields for plotting, defined in cedar_graph package.
    """
    # system -> data file
    start_time = time_config.start_time
    forecast_time = time_config.forecast_time

    data_source = ExprLocalDataSource(expr_config=expr_config)
    data_loader = DataLoader(data_source=data_source)

    plot_data = load_data(data_loader=data_loader, start_time=start_time, forecast_time=forecast_time)
    return plot_data
