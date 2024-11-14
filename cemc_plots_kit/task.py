from pathlib import Path

import yaml
import pandas as pd

from cedarkit.maps.util import AreaRange

from cemc_plots_kit.logger import get_logger
from cemc_plots_kit.config import (
    ExprConfig, PlotConfig, TimeConfig, JobConfig, parse_start_time, RuntimeConfig,
    get_default_data_file_name_template,
)
from cemc_plots_kit.job import run_job
from cemc_plots_kit.plots import get_plot_module


task_logger = get_logger(__name__)


def run_task(task_file_path: Path):
    """
    Run plot tasks defined in task file. Execute the following steps:

    * load task file
    * generate experiment configuration object and runtime configuration object
    * generate plot list from the task file, and load plotting module for each plot type
    * generate plot job list according to time configuration,
      and use ``check_available`` function in plot module to filter out invalid time combinations.
    * call ``run_by_serial`` to run all plot jobs in serial

    Parameters
    ----------
    task_file_path
        task file path
    """
    task_config = load_task_config(task_file_path=task_file_path)

    area = None
    if "area" in task_config:
        area_config = task_config["area"]
        area = AreaRange(
            start_latitude=area_config["start_latitude"],
            end_latitude=area_config["end_latitude"],
            start_longitude=area_config["start_longitude"],
            end_longitude=area_config["end_longitude"],
        )
    system_name = task_config["system_name"]
    data_file_name_template = task_config["source"].get("data_file_name_template", None)
    if data_file_name_template is None:
        data_file_name_template = get_default_data_file_name_template(system_name=system_name)
    if data_file_name_template is None:
        raise ValueError(f"Can't get default data_file_name_template with system_name {system_name}."
                         f"Please set data_file_name_template parameter.")
    expr_config = ExprConfig(
        system_name=system_name,
        area=area,
        data_dir=task_config["source"]["data_dir"],
        data_file_name_template=data_file_name_template,
    )

    task_runtime_config = task_config["runtime"]
    if "base_work_dir" in task_runtime_config:
        task_runtime_config["base_work_dir"] = Path(task_runtime_config["base_work_dir"]).absolute()
    runtime_config = RuntimeConfig(
        **task_runtime_config,
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
                task_logger.debug(f"skip job because of time: [{plot_name}] [{start_time}] [{forecast_time}]")
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
    Load task configuration from task file, return dict object.

    Parameters
    ----------
    task_file_path
        task file path

    Returns
    -------
    dict
        task configuration dict
    """
    with open(task_file_path) as task_file:
        task_config = yaml.safe_load(task_file)
        return task_config


def run_by_serial(job_configs: list[JobConfig]):
    """
    Execute all jobs in job list.

    Parameters
    ----------
    job_configs
        job list, one item represents one job.
    """
    count = len(job_configs)
    for i, job_config in enumerate(job_configs):
        task_logger.info(f"job {i+1}/{count} start...")
        task_logger.info(f"  [{job_config.plot_config.plot_name}] "
                         f"[{job_config.time_config.start_time}] "
                         f"[{job_config.time_config.forecast_time}]")
        job_start_time = pd.Timestamp.now()
        output_image_file_path = run_job(job_config=job_config)
        job_end_time = pd.Timestamp.now()
        task_logger.info(f"job {i+1}/{count} done. time: {job_end_time - job_start_time}")
