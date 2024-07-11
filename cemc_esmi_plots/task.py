from pathlib import Path
from typing import Dict, List

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


def load_task_config(task_file_path: Path) -> Dict:
    with open(task_file_path) as task_file:
        task_config = yaml.safe_load(task_file)
        return task_config


def run_by_serial(job_configs: List[JobConfig]):
    count = len(job_configs)
    for i, job_config in enumerate(job_configs):
        task_logger.info(f"job {i+1}/{count} start...")
        task_logger.info(f"  [{job_config.plot_config.plot_name}] "
                         f"[{job_config.time_config.start_time}] "
                         f"[{job_config.time_config.forecast_time}]")
        output_image_file_path = run_job(job_config=job_config)
        task_logger.info(f"job {i+1}/{count} done")
