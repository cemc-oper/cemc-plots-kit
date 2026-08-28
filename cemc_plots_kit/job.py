from pathlib import Path
import inspect
import os

import pandas as pd
import matplotlib.pyplot as plt

from cedarkit.plots.chart import Panel
from cedar_graph.data import DataLoader, DataSource, RekiProvider

from cemc_plots_kit.config import JobConfig, ExprConfig
from cemc_plots_kit.plots import get_plot_definition, get_plot_label
from cemc_plots_kit.source import ExprLocalDataSource
from cemc_plots_kit.logger import get_logger


job_logger = get_logger("job")


def run_job(job_config: JobConfig) -> list[Path]:
    """
    Run a plot job, involves the following steps:

    * create working directory
    * create a directory fore saving output figure
    * resolve plot definition (recipe or Python module) from ``plot_name``
    * enter working directory
    * run plot (build data source → load data → plot)
    * save the result figure
    * clean memory
    * enter current directory

    Parameters
    ----------
    job_config
        job configuration which represents a single plot job.

    Returns
    -------
    List[Path]
        path list for generated figures.
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
    job_logger.info(f"resolving plot definition... {plot_name}")
    plot_definition = get_plot_definition(
        plot_name=plot_name,
        base_dir=plot_config.base_dir,
    )

    previous_dir = os.getcwd()

    job_logger.info(f"entering work dir... {current_work_dir}")
    os.chdir(current_work_dir)

    try:
        job_logger.info(f"running plot job...")
        panel = run_plot(plot_definition=plot_definition, job_config=job_config)

        job_logger.info(f"saving output image... {output_image_file_path}")
        panel.save(output_image_file_path)
    finally:
        # A task must never leak its per-job directory to the next task, even
        # when loading, plotting, or saving raises.
        plt.clf()
        plt.close("all")
        job_logger.info(f"exiting work dir... {previous_dir}")
        os.chdir(previous_dir)

    return [output_image_file_path]


def run_plot(plot_definition, job_config: JobConfig) -> Panel:
    """
    Run a resolved plot definition for one job: build the experiment data
    source, load fields through the definition's ``load_data`` and draw
    with its ``plot``. Works uniformly for engine recipes and Python
    plot modules; recipe parameters come from ``plot_config.plot_params``.
    """
    expr_config = job_config.expr_config
    time_config = job_config.time_config
    plot_config = job_config.plot_config

    metadata_kwargs = dict(
        start_time=time_config.start_time,
        forecast_time=time_config.forecast_time,
        system_name=expr_config.system_name,
        area_range=expr_config.area,
        **plot_config.plot_params,
    )

    metadata_class = plot_definition.PlotMetadata
    metadata_fields = set(inspect.signature(metadata_class).parameters)
    metadata = metadata_class(**{
        key: value for key, value in metadata_kwargs.items() if key in metadata_fields
    })

    job_logger.info("loading data...")
    data_source = create_data_source(expr_config=expr_config)
    data_loader = (
        DataLoader(provider=data_source)
        if isinstance(data_source, RekiProvider)
        else DataLoader(data_source=data_source)
    )

    load_data_params = set(inspect.signature(plot_definition.load_data).parameters)
    load_data_kwargs = {
        key: value for key, value in metadata_kwargs.items() if key in load_data_params
    }
    plot_data = plot_definition.load_data(data_loader=data_loader, **load_data_kwargs)
    job_logger.info("loading data...done")

    job_logger.info("plotting...")
    panel = plot_definition.plot(plot_data=plot_data, plot_metadata=metadata)
    job_logger.info("plotting...done")

    del plot_data
    return panel


def create_data_source(expr_config: ExprConfig) -> DataSource:
    """
    Create the experiment local data source.

    Kept as a separate function so tests can substitute a mock data source.
    """
    if expr_config.source_spec is not None:
        return RekiProvider(expr_config.source_spec)
    return ExprLocalDataSource(expr_config=expr_config)


def create_work_dir(job_config: JobConfig) -> Path:
    """
    Create a working directory for a plot job using ``base_work_dir``.
    Directory location ``{base_work_dir}/{start_time_label}/{plot_label}/{forecast_time_label}``

    Parameters
    ----------
    job_config
        job configuration which represents a single plot job.

    Returns
    -------
    Path
        working directory.
    """
    base_work_dir = job_config.runtime_config.base_work_dir
    time_config = job_config.time_config
    start_time = time_config.start_time
    start_time_label = start_time.strftime("%Y%m%d%H%M")
    forecast_time = time_config.forecast_time
    forecast_time_label = f"{int(forecast_time / pd.Timedelta(hours=1)):03d}"

    plot_label = get_plot_label(
        plot_name=job_config.plot_config.plot_name,
        plot_params=job_config.plot_config.plot_params,
    )

    current_work_dir = Path(base_work_dir, start_time_label, plot_label, forecast_time_label)
    current_work_dir.mkdir(parents=True, exist_ok=True)
    return current_work_dir


def create_output_image_dir(job_config: JobConfig) -> Path:
    """
    Create the output image directory for saving.
    Directory location ``{base_work_dir}/output``.

    Parameters
    ----------
    job_config
        job configuration which represents a single plot job.

    Returns
    -------
    Path
        output image directory.
    """
    base_work_dir = job_config.runtime_config.base_work_dir
    output_image_dir = Path(base_work_dir, "output")
    output_image_dir.mkdir(parents=True, exist_ok=True)
    return  output_image_dir


def get_output_image_file_name(job_config: JobConfig) -> str:
    """
    Generate output image file name using job configuration.
    ``{plot_label}_{start_time_label}_{forecast_time_label}.png``

    Parameters
    ----------
    job_config
        job configuration which represents a single plot job.

    Returns
    -------
    str
        output image file path.
    """
    time_config = job_config.time_config
    plot_config = job_config.plot_config

    plot_label = get_plot_label(
        plot_name=plot_config.plot_name,
        plot_params=plot_config.plot_params,
    )

    start_time = time_config.start_time
    start_time_label = start_time.strftime("%Y%m%d%H")
    forecast_time = time_config.forecast_time
    forecast_time_label = f"{int(forecast_time / pd.Timedelta(hours=1)):03d}"

    file_name = f"{plot_label}_{start_time_label}_{forecast_time_label}.png"
    return file_name
