from cedarkit.maps.chart import Panel

from cedar_graph.data import DataLoader
from cedar_graph.plots.cn.height_500_mslp.default import PlotData, PlotMetadata, plot, load_data

from cemc_esmi_plots.source import ExprLocalDataSource
from cemc_esmi_plots.config import PlotConfig, TimeConfig, ExprConfig, JobConfig
from cemc_esmi_plots.logger import get_logger


# set_default_map_loader_package("cedarkit.maps.map.cemc")
PLOT_NAME = "height_500_mslp"
plot_logger = get_logger(PLOT_NAME)


def run_plot(job_config: JobConfig) -> Panel:
    """
    根据作业配置 (``job_config``) 绘制图片。

    Parameters
    ----------
    job_config
        作业配置

    Returns
    -------
    Panel
        绘图板
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
    检查是否可以用时间组合绘制当前图片，比如 24 小时降水要求预报时效大于等于 24 小时。

    Parameters
    ----------
    time_config
    plot_config

    Returns
    -------
    bool
        是否可以绘制
    """
    return True


def _load(expr_config: ExprConfig, time_config: TimeConfig) -> PlotData:
    """
    从实验数据中加载绘图需要的要素场

    Parameters
    ----------
    expr_config
        试验信息，用于创建 ``ExprLocalDataSource``
    time_config
        时间信息

    Returns
    -------
    PlotData
        绘图需要的要素场，由 cedar_graph 包定义
    """
    # system -> data file
    start_time = time_config.start_time
    forecast_time = time_config.forecast_time

    data_source = ExprLocalDataSource(expr_config=expr_config)
    data_loader = DataLoader(data_source=data_source)

    plot_data = load_data(data_loader=data_loader, start_time=start_time, forecast_time=forecast_time)
    return plot_data
