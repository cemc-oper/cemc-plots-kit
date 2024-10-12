from pathlib import Path
import os

import pandas as pd
import matplotlib.pyplot as plt

from cemc_plots_kit.config import JobConfig
from cemc_plots_kit.plots import get_plot_module
from cemc_plots_kit.logger import get_logger


job_logger = get_logger("job")


def run_job(job_config: JobConfig) -> list[Path]:
    """
    运行一个绘图作业，包括如下步骤：

    * 创建工作目录
    * 创建输入图片保存目录
    * 加载绘图模块
    * 进入到工作目录
    * 执行绘图函数
    * 保存图片结果
    * 清理内存
    * 恢复当前目录

    Parameters
    ----------
    job_config
        作业配置，代表一个绘图作业

    Returns
    -------
    List[Path]
        生成的图片路径列表
    """
    runtime_config = job_config.runtime_config
    plot_config = job_config.plot_config

    job_logger.info("creating work dir...")
    work_dir = runtime_config.work_dir
    if work_dir is None:
        current_work_dir = create_work_dir(job_config=job_config)
    else:
        current_work_dir = Path(work_dir)
        current_work_dir.mkdir(exist_ok=True, parents=True)
    job_logger.info(f"creating work dir... {current_work_dir}")

    job_logger.info("creating output image dir...")
    output_image_dir = runtime_config.output_dir
    if output_image_dir is None:
        output_image_dir = create_output_image_dir(job_config=job_config)
    else:
        output_image_dir = Path(output_image_dir)
        output_image_dir.mkdir(exist_ok=True, parents=True)
    job_logger.info(f"creating output image dir... {output_image_dir}")

    output_image_file_name = get_output_image_file_name(job_config=job_config)
    output_image_file_path = Path(output_image_dir, output_image_file_name)
    job_logger.info(f"output image file name: {output_image_file_name}")

    plot_name = plot_config.plot_name
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
    为一个绘图作业创建运行目录，目录位置 ``{base_work_dir}/{start_time_label}/{plot_name}/{forecast_time_label}``

    Parameters
    ----------
    job_config
        作业配置

    Returns
    -------
    Path
        运行目录
    """
    base_work_dir = job_config.runtime_config.base_work_dir
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
    创建输出图片保存目录，目录路径 ``{base_work_dir}/output``

    Parameters
    ----------
    job_config
        作业配置

    Returns
    -------
    Path
        输出图片保存目录
    """
    base_work_dir = job_config.runtime_config.base_work_dir
    output_image_dir = Path(base_work_dir, "output")
    output_image_dir.mkdir(parents=True, exist_ok=True)
    return  output_image_dir


def get_output_image_file_name(job_config: JobConfig) -> str:
    """
    使用作业配置信息生成输出图片文件名

    Parameters
    ----------
    job_config
        作业配置

    Returns
    -------
    str
        输出图片文件名
    """
    time_config = job_config.time_config
    plot_config = job_config.plot_config

    plot_name = plot_config.plot_name

    start_time = time_config.start_time
    start_time_label = start_time.strftime("%Y%m%d%H")
    forecast_time = time_config.forecast_time
    forecast_time_label = f"{int(forecast_time / pd.Timedelta(hours=1)):03d}"

    file_name = f"{plot_name}_{start_time_label}_{forecast_time_label}.png"
    return file_name
