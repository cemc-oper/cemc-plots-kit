from pathlib import Path
import os

import pandas as pd
import matplotlib.pyplot as plt

from cemc_esmi_plots.config import JobConfig
from cemc_esmi_plots.plots import get_plot_module
from cemc_esmi_plots.logger import get_logger


job_logger = get_logger("job")


def run_job(job_config: JobConfig) -> list[Path]:
    """
    运行一个绘图任务

    Parameters
    ----------
    job_config

    Returns
    -------
    List[Path]
        生成的图片路径列表
    """
    job_logger.info("creating work dir...")
    current_work_dir = create_work_dir(job_config=job_config)
    job_logger.info(f"creating work dir... {current_work_dir}")

    job_logger.info("creating output image dir...")
    output_image_dir = create_output_image_dir(job_config=job_config)
    job_logger.info(f"creating output image dir... {output_image_dir}")

    output_image_file_name = get_output_image_file_name(job_config=job_config)
    output_image_file_path = Path(output_image_dir, output_image_file_name)
    job_logger.info(f"output image file name: {output_image_file_name}")

    plot_name = job_config.plot_config.plot_name
    job_logger.info(f"loading plot module...")
    plot_module = get_plot_module(plot_name=plot_name)
    job_logger.info(f"get plot module: {plot_module.__name__}")

    previous_dir = os.getcwd()

    job_logger.info(f"entering work dir... {current_work_dir}")
    os.chdir(current_work_dir)
    job_logger.info(f"running plot job...")
    panel = plot_module.run_plot(job_config=job_config)

    job_logger.info(f"saving output image... {output_image_file_path}")
    panel.save(output_image_file_path)

    # clear memory
    plt.clf()
    plt.close("all")
    del panel
    del plot_module

    job_logger.info(f"exiting work dir... {previous_dir}")
    os.chdir(previous_dir)

    return [output_image_file_path]


def create_work_dir(job_config: JobConfig) -> Path:
    """
    为一个绘图任务创建运行目录

    Parameters
    ----------
    job_config

    Returns
    -------
    Path
    """
    base_work_dir = job_config.runtime_config.work_dir
    time_config = job_config.time_config
    start_time = time_config.start_time
    start_time_label = start_time.strftime("%Y%m%d%H%M")
    forecast_time = time_config.forecast_time
    forecast_time_label = f"{int(forecast_time / pd.Timedelta(hours=1)):03d}"

    plot_name = job_config.plot_config.plot_name

    current_work_dir = Path(base_work_dir, start_time_label, plot_name, forecast_time_label)
    current_work_dir.mkdir(parents=True, exist_ok=True)
    return current_work_dir


def create_output_image_dir(job_config: JobConfig) -> Path:
    """
    创建输出图片保存目录

    Parameters
    ----------
    job_config

    Returns
    -------
    Path
    """
    base_work_dir = job_config.runtime_config.work_dir
    output_image_dir = Path(base_work_dir, "output")
    output_image_dir.mkdir(parents=True, exist_ok=True)
    return  output_image_dir


def get_output_image_file_name(job_config: JobConfig) -> str:
    """
    返回输出图片的文件名

    Parameters
    ----------
    job_config

    Returns
    -------
    str
    """
    time_config = job_config.time_config
    start_time = time_config.start_time
    start_time_label = start_time.strftime("%Y%m%d%H")
    forecast_time = time_config.forecast_time
    forecast_time_label = f"{int(forecast_time / pd.Timedelta(hours=1)):03d}"

    plot_name = job_config.plot_config.plot_name

    file_name = f"{plot_name}_{start_time_label}_{forecast_time_label}.png"
    return file_name
