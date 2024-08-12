from pathlib import Path

import yaml
import pandas as pd

from cedarkit.maps.util import AreaRange

from cemc_esmi_plots.logger import get_logger
from cemc_esmi_plots.config import (
    ExprConfig, PlotConfig, TimeConfig, JobConfig, parse_start_time, RuntimeConfig
)
from cemc_esmi_plots.job import run_job
from cemc_esmi_plots.plots import get_plot_module


task_logger = get_logger(__name__)


def run_task(task_file_path: Path):
    """
    执行任务文件中定义的绘图任务。执行如下步骤

    * 加载任务文件
    * 从任务文件生成试验配置对象和运行时配置对象
    * 从任务文件生成绘图清单，并为每类绘图加载绘图模块
    * 根据时间参数生成绘图作业列表，使用绘图模块的 ``check_available`` 函数过滤无效的时间组合
    * 调用 ``run_by_serial`` 串行执行所有绘图作业

    Parameters
    ----------
    task_file_path
        任务文件路径
    """
    task_config = load_task_config(task_file_path=task_file_path)

    area_config = task_config["area"]
    area = AreaRange(
        start_latitude=area_config["start_latitude"],
        end_latitude=area_config["end_latitude"],
        start_longitude=area_config["start_longitude"],
        end_longitude=area_config["end_longitude"],
    )

    grib2_file_name_template = task_config["source"].get("grib2_file_name_template", None)
    expr_config = ExprConfig(
        system_name=task_config["system_name"],
        area=area,
        source_grib2_dir=task_config["source"]["grib2_dir"],
        grib2_file_name_template=grib2_file_name_template,
    )

    runtime_config = RuntimeConfig(
        work_dir=task_config["runtime"]["work_dir"],
    )

    time_config = task_config["time"]
    start_time = parse_start_time(str(time_config["start_time"]))
    total_forecast_time = pd.to_timedelta(time_config["forecast_time"])
    forecast_interval = pd.to_timedelta(time_config["forecast_interval"])
    forecast_times = pd.timedelta_range("0h", total_forecast_time, freq=forecast_interval)

    plots_config = task_config["plots"]
    selected_plots = []
    for plot_name,v in plots_config.items():
        if not v:
            continue
        plot_module = get_plot_module(plot_name=plot_name)
        selected_plots.append({
            "plot_name": plot_name,
            "plot_module": plot_module,
        })

    task_logger.info(f"selected plots: {selected_plots}")

    job_configs = []
    for forecast_time in forecast_times:
        time_config = TimeConfig(
            start_time=start_time,
            forecast_time=forecast_time,
        )
        for current_plot in selected_plots:
            plot_module = current_plot["plot_module"]
            plot_name = current_plot["plot_name"]
            plot_config = PlotConfig(plot_name=plot_name)

            if not plot_module.check_available(time_config=time_config, plot_config=plot_config):
                task_logger.debug(f"skip job because of time: {plot_name} {start_time} {forecast_time}")
                continue

            job_config = JobConfig(
                expr_config=expr_config,
                time_config=time_config,
                runtime_config=runtime_config,
                plot_config=plot_config,
            )
            job_configs.append(job_config)

    task_logger.info(f"get {len(job_configs)} jobs")

    task_logger.info("begin to run jobs...")
    run_by_serial(job_configs=job_configs)
    task_logger.info("end jobs")


def load_task_config(task_file_path: Path) -> dict:
    """
    从任务文件中加载任务配置，返回字典对象

    Parameters
    ----------
    task_file_path
        任务文件路径

    Returns
    -------
    dict
        任务配置
    """
    with open(task_file_path) as task_file:
        task_config = yaml.safe_load(task_file)
        return task_config


def run_by_serial(job_configs: list[JobConfig]):
    """
    顺序运行作业列表中的所有作业

    Parameters
    ----------
    job_configs
        作业列表，一个对象代表一个作业
    """
    count = len(job_configs)
    for i, job_config in enumerate(job_configs):
        task_logger.info(f"job {i+1}/{count} start...")
        task_logger.info(f"  [{job_config.plot_config.plot_name}] "
                         f"[{job_config.time_config.start_time}] "
                         f"[{job_config.time_config.forecast_time}]")
        output_image_file_path = run_job(job_config=job_config)
        task_logger.info(f"job {i+1}/{count} done")
