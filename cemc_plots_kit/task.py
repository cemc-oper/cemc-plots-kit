from pathlib import Path

import yaml
import pandas as pd
import reki

from cedarkit.plots.types import AreaRange

from cemc_plots_kit.logger import get_logger
from cemc_plots_kit.config import (
    ExprConfig, PlotConfig, TimeConfig, JobConfig, parse_start_time, RuntimeConfig,
    get_default_data_file_name_template, get_default_data_dir,
)
from cemc_plots_kit.job import run_job
from cemc_plots_kit.plots import get_plot_definition, check_plot_available


task_logger = get_logger(__name__)


def run_task(task_file_path: Path):
    """
    Run plot tasks defined in task file. Execute the following steps:

    * load task file
    * generate experiment configuration object and runtime configuration object
    * parse the ``plots`` section into (plot type, params) entries and resolve
      the plot definition (recipe or Python module) for each entry
    * generate plot job list according to time configuration,
      and use ``check_available`` of each plot definition to filter out invalid time combinations.
    * call ``run_by_serial`` to run all plot jobs in serial

    Parameters
    ----------
    task_file_path
        task file path
    """
    task_file_path = Path(task_file_path)
    task_config = load_task_config(task_file_path=task_file_path)
    if task_config.get("api_version") == "cemc.plots/v2":
        from cemc_plots_kit.execution import run_task_spec
        from cemc_plots_kit.task_spec import load_task_spec
        return run_task_spec(load_task_spec(task_file_path), task_file=task_file_path)

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
    expr_config = bind_task_source(
        system_name=system_name,
        source_config=task_config.get("source", {}),
        base_dir=task_file_path.parent,
        area=area,
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

    selected_plots = []
    for plot_name, plot_params in parse_plots_config(task_config["plots"]):
        plot_definition = get_plot_definition(
            plot_name=plot_name,
            base_dir=task_file_path.parent,
        )
        selected_plots.append({
            "plot_name": plot_name,
            "plot_params": plot_params,
            "plot_definition": plot_definition,
        })

    task_logger.info(f"selected plots: {[p['plot_name'] for p in selected_plots]}")

    job_configs = []
    for forecast_time in forecast_times:
        time_config = TimeConfig(
            start_time=start_time,
            forecast_time=forecast_time,
        )
        for current_plot in selected_plots:
            plot_name = current_plot["plot_name"]
            plot_config = PlotConfig(
                plot_name=plot_name,
                plot_params=current_plot["plot_params"],
                base_dir=task_file_path.parent,
            )

            if not check_plot_available(
                    plot_definition=current_plot["plot_definition"],
                    time_config=time_config,
                    plot_config=plot_config,
            ):
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


def parse_plots_config(plots_config: dict) -> list[tuple[str, dict]]:
    """
    Parse the ``plots`` section of a task file into ``(plot_name, params)`` entries.

    Each key is a plot type (``cn.t2m``, ``cn.shr.default``) or an external
    recipe path (``.yaml``/``.yml``). The value selects and parameterizes it:

    * bool: ``on``/``off`` switch without parameters
    * mapping: recipe parameters, e.g. ``{interval: 3h}``
    * list of mappings: several parameter sets of the same plot,
      e.g. multiple precipitation intervals

    Parameters
    ----------
    plots_config
        the ``plots`` mapping from a task file.

    Returns
    -------
    list[tuple[str, dict]]
        enabled ``(plot_name, plot_params)`` entries, in file order.
    """
    selected = []
    for plot_name, value in plots_config.items():
        if isinstance(value, str):
            # YAML 1.1 的 on/off 已被 PyYAML 解析为 bool；字符串形式兜底
            value = value.strip().lower() not in ("off", "false", "no", "0")
        if value is None or value is False:
            continue
        if value is True:
            selected.append((plot_name, {}))
        elif isinstance(value, dict):
            selected.append((plot_name, dict(value)))
        elif isinstance(value, list):
            for item in value:
                selected.append((plot_name, dict(item) if item else {}))
        else:
            raise ValueError(
                f"invalid plots entry for {plot_name!r}: {value!r}; "
                f"expected on/off, a params mapping or a list of params mappings"
            )
    return selected


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


def bind_task_source(
        system_name: str, source_config: dict | None, base_dir: Path,
        area: AreaRange | None = None,
) -> ExprConfig:
    """Bind a v1 task source to one explicit :class:`reki.SourceSpec`.

    A legacy pair of ``data_dir`` and ``data_file_name_template`` is an
    explicit ``file-pattern`` binding.  Missing members are filled only from
    the resolved catalog record; no implicit nested merge is performed.  With
    no explicit path fields the catalog's own source is used.
    """
    source_config = dict(source_config or {})
    try:
        resolved = reki.load_catalog(plugins=False, user=False).resolve(system_name)
    except KeyError as exc:
        if "data_dir" not in source_config or "data_file_name_template" not in source_config:
            raise ValueError(
                f"unknown dataset {system_name!r}; provide both data_dir and "
                "data_file_name_template for an explicit file-pattern source"
            ) from exc
        resolved = None

    data_dir = source_config.get("data_dir")
    template = source_config.get("data_file_name_template")
    if resolved is not None:
        data_dir = data_dir if data_dir is not None else get_default_data_dir(system_name)
        template = template if template is not None else get_default_data_file_name_template(system_name)

    if ("data_dir" in source_config) != ("data_file_name_template" in source_config):
        # A partial explicit v1 source deliberately has exactly one catalog
        # default.  The error identifies the unsupported case instead of
        # silently selecting an unrelated dataset default.
        if data_dir is None or template is None:
            raise ValueError(
                f"incomplete explicit source for {system_name!r}: catalog has "
                "no matching default for the missing value"
            )

    if "data_dir" in source_config or "data_file_name_template" in source_config:
        if data_dir is None or template is None:
            raise ValueError(
                "explicit file-pattern source requires data_dir and "
                "data_file_name_template"
            )
        data_dir = Path(data_dir)
        if not data_dir.is_absolute():
            data_dir = base_dir / data_dir
        source_spec = reki.SourceSpec("file-pattern", (str(data_dir), template))
        dataset_id = resolved.record.dataset_id if resolved is not None else None
    else:
        if resolved is None:
            raise AssertionError("unreachable")
        source_spec = resolved.source
        dataset_id = resolved.record.dataset_id

    return ExprConfig(
        system_name=system_name,
        area=area,
        data_dir=data_dir,
        data_file_name_template=template,
        source_spec=source_spec,
        dataset_id=dataset_id,
    )


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
