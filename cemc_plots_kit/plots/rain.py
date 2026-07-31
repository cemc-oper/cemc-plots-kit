"""
降水+10米风图形，按降水累计时段参数化。

覆盖 ``rain_{n}h_wind_10m`` 系列图形（n 为降水累计小时数），
由 ``cemc_plots_kit.plots.get_plot_module`` 按图名解析时段后构造。
"""
import pandas as pd

from cedarkit.plots.chart import Panel

from cedar_graph.data import DataLoader
from cedar_graph.plots.cn.rain_wind_10m.default import PlotData, PlotMetadata, plot, load_data

from cemc_plots_kit.source import ExprLocalDataSource
from cemc_plots_kit.config import PlotConfig, TimeConfig, ExprConfig, JobConfig
from cemc_plots_kit.logger import get_logger


class RainPlotModule:
    """
    参数化的降水+10米风绘图模块，接口与静态绘图模块一致。

    Parameters
    ----------
    interval_hours : int
        降水累计时段（小时）。
    """
    def __init__(self, interval_hours: int):
        self.interval = pd.Timedelta(hours=interval_hours)
        self.__name__ = f"cemc_plots_kit.plots.rain_{interval_hours}h_wind_10m"
        self.plot_logger = get_logger(self.__name__)

    def run_plot(self, job_config: JobConfig) -> Panel:
        expr_config = job_config.expr_config
        time_config = job_config.time_config

        system_name = expr_config.system_name
        start_time = time_config.start_time
        forecast_time = time_config.forecast_time

        metadata = PlotMetadata(
            start_time=start_time,
            forecast_time=forecast_time,
            system_name=system_name,
            area_range=expr_config.area,
            interval=self.interval,
        )

        self.plot_logger.info("loading data...")
        plot_data = self.load(
            expr_config=expr_config,
            time_config=time_config,
        )
        self.plot_logger.info("loading data...done")

        # field -> plot
        self.plot_logger.info("plotting...")
        panel = plot(
            plot_data=plot_data,
            plot_metadata=metadata,
        )
        self.plot_logger.info("plotting...done")

        del plot_data

        # plot -> output
        return panel

    def check_available(self, time_config: TimeConfig, plot_config: PlotConfig) -> bool:
        return time_config.forecast_time >= self.interval

    def load(self, expr_config: ExprConfig, time_config: TimeConfig) -> PlotData:
        # system -> data file
        start_time = time_config.start_time
        forecast_time = time_config.forecast_time

        data_source = ExprLocalDataSource(expr_config=expr_config)
        data_loader = DataLoader(data_source=data_source)

        plot_data = load_data(
            data_loader=data_loader,
            start_time=start_time,
            forecast_time=forecast_time,
            interval=self.interval,
        )
        return plot_data


def create_plot_module(interval_hours: int) -> RainPlotModule:
    """按降水累计时段（小时）创建绘图模块。"""
    return RainPlotModule(interval_hours=interval_hours)
