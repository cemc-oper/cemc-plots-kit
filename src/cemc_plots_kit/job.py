from pathlib import Path
from dataclasses import asdict
import os
from uuid import uuid4

import pandas as pd

from cedarkit.plots.chart import Panel
from cedar_graph.data import RekiProvider

from cemc_plots_kit.config import JobConfig, ExprConfig
from cemc_plots_kit.plots import (EnsembleRequest, EnsembleT2MProduct, WorkflowProduct,
                                  get_plot_definition, get_plot_label, workflow_context)
from cemc_plots_kit.logger import get_logger


job_logger = get_logger("job")


def run_job(job_config: JobConfig, *, data_source=None) -> list[Path]:
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

    temporary_path = None
    owned_provider = None
    try:
        job_logger.info(f"running plot job...")
        if data_source is None and isinstance(plot_definition, (WorkflowProduct, EnsembleT2MProduct)):
            owned_provider = create_data_source(expr_config=job_config.expr_config)
        panel = run_plot(plot_definition=plot_definition, job_config=job_config,
                         data_source=owned_provider if owned_provider is not None else data_source)

        job_logger.info(f"saving output image... {output_image_file_path}")
        temporary_path = output_image_file_path.with_name(
            f".{output_image_file_path.stem}.{uuid4().hex}.tmp{output_image_file_path.suffix}"
        )
        panel.save(temporary_path)
        os.replace(temporary_path, output_image_file_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
        # This job owns only its own panel.  Closing all pyplot figures would
        # incorrectly dispose of a caller's unrelated figure.
        owned_panel = locals().get("panel")
        if owned_panel is not None:
            owned_panel.close()
        if owned_provider is not None and hasattr(owned_provider, "close"):
            owned_provider.close()

    return [output_image_file_path]


def run_plot(plot_definition, job_config: JobConfig, *, data_source=None) -> Panel:
    """Run one selected v3 product with a caller or job-owned provider."""
    expr_config = job_config.expr_config
    time_config = job_config.time_config
    plot_config = job_config.plot_config

    if isinstance(plot_definition, EnsembleT2MProduct):
        provider = data_source if data_source is not None else create_data_source(expr_config=expr_config)
        prepared = plot_definition.prepare(provider, start_time=time_config.start_time,
                                           forecast_time=time_config.forecast_time,
                                           request=EnsembleRequest.from_params(plot_config.plot_params))
        return prepared.render()

    if isinstance(plot_definition, WorkflowProduct):
        provider = data_source if data_source is not None else create_data_source(expr_config=expr_config)
        if not hasattr(provider, "fetch_many") and not hasattr(provider, "fetch"):
            raise TypeError("workflow product requires a field request provider")
        return plot_definition.run(provider, workflow_context(time_config, plot_config))

    raise TypeError("plot definition must be a v3 product")


def create_data_source(expr_config: ExprConfig) -> RekiProvider:
    """
    Create the experiment local data source.

    Kept as a separate function so tests can substitute a mock data source.
    """
    if expr_config.source_spec is None:
        raise ValueError("a reki SourceSpec is required for v3 products")
    return RekiProvider(expr_config.source_spec,
                        region=asdict(expr_config.area) if expr_config.area is not None else None)


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
