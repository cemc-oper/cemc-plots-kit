from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Union

import pandas as pd
import reki


from cedarkit.plots.types import AreaRange


@dataclass
class ExprConfig:
    """
    Experiment parameters which remains consistent for all data in the experiment.

    Attributes
    ----------
    system_name
        Name of the system which will be shown in top left of the figure.
    data_dir
        Path to the data directory, may be a template.
    area
        Plot area, default is CN.
    data_file_name_template
        File name template for data.
    """
    system_name: str
    data_dir: Union[str, Path]
    area: Optional[AreaRange] = None
    data_file_name_template: Optional[str] = None
    # ``source_spec`` is the canonical data binding for task v1.  Keep the
    # two legacy path fields above so callers can still construct this class
    # directly and ``ExprLocalDataSource`` remains usable.
    source_spec: Optional[reki.SourceSpec] = None
    dataset_id: Optional[str] = None


@dataclass
class RuntimeConfig:
    """
    Runtime parameters, one object for each type of plot.

    base_work_dir
        Base directory for plots, used if ``work_dir`` is not specified.
    work_dir
        Directory for some plot.
    output_dir
        Figures will be saved to this directory.
    """
    base_work_dir: Optional[Union[str, Path]] = None
    work_dir: Optional[Union[str, Path]]  = None
    output_dir: Optional[Union[str, Path]]  = None


@dataclass
class TimeConfig:
    """
    Time parameters to plot figures for different start time and different forecast time, one object for one figure.

    Attributes
    ----------
    start_time
    forecast_time
    """
    start_time: pd.Timestamp
    forecast_time: pd.Timedelta


@dataclass
class PlotConfig:
    """
    Plot parameters, defining customized parameters for plotting, one object for each type of plot.

    plot_name
        v3 product ID (e.g. ``cn.t2m``, ``cn.shr.default``, ``cn.ens_t2m``)
        or an external v3 recipe file path (``.yaml``/``.yml``).
    plot_params
        Product parameter values, e.g. ``{"interval": "3h"}`` for ``cn.rain_wind_10m``
        or ``{"member_ids": ["m01"]}`` for ``cn.ens_t2m``.
    base_dir
        Base directory for resolving relative external recipe paths,
        usually the task file directory. ``None`` resolves against the
        current working directory.
    """
    plot_name: str
    plot_params: dict = field(default_factory=dict)
    base_dir: Optional[Union[str, Path]] = None


@dataclass
class JobConfig:
    """
    Config information for each plot job, including:

    * Experiment configuration
    * Time parameters
    * Runtime parameters
    * Plot parameters

    Attributes
    ----------
    expr_config
    time_config
    runtime_config
    plot_config
    """
    expr_config: ExprConfig
    time_config: TimeConfig
    runtime_config: RuntimeConfig
    plot_config: PlotConfig


def parse_start_time(start_time_str: str) -> pd.Timestamp:
    """
    Parse start time string.

    Parameters
    ----------
    start_time_str
        Start time string, supportting format:

        * YYYYMMDDHHMM: Year month day hour miniute
        * YYYYMMDDHH: Year month day hour

    Returns
    -------
    pd.Timestamp
        Parsed time object

    Examples
    --------
    Year month day hour minute

    >>> parse_start_time("202409230000")
    Timestamp('2024-09-23 00:00:00')

    Year month day hour

    >>> parse_start_time("2024092300")
    Timestamp('2024-09-23 00:00:00')

    Year month day

    >>> parse_start_time("20240923")
    Timestamp('2024-09-23 00:00:00')

    """
    if len(start_time_str) == 12:
        format_str = "%Y%m%d%H%M"
    elif len(start_time_str) == 10:
        format_str = "%Y%m%d%H"
    elif len(start_time_str) == 8:
        format_str = "%Y%m%d"
    else:
        raise ValueError(f"start time string is not supported: {start_time_str}")
    return pd.to_datetime(start_time_str, format=format_str)


def get_default_data_file_name_template(system_name: str) -> Optional[str]:
    """
    Return the default data filename template.

    Parameters
    ----------
    system_name
        name of system, supporting:

        * cma_gfs, cma_gfs_gmf
        * cma_meso, cma_meso_3km, cma_meso_1km
        * cma_tym

    Returns
    -------
    Optional[str]
        data file name template. If system name is not supported, return None.
    """
    try:
        record = reki.load_catalog(plugins=False, user=False).resolve(system_name).record
    except KeyError:
        return None
    return record.metadata.get("legacy_file_name_template")


def get_default_data_dir(system_name: str) -> Optional[str]:
    """
    Return default data directory. Default data is stored in CMA-HPC SC1.

    Parameters
    ----------
    system_name
        name of system, supporting:

        * cma_gfs, cma_gfs_gmf
        * cma_meso, cma_meso_3km, cma_meso_1km
        * cma_tym

    Returns
    -------
    Optional[str]
        data file path. If system name is not supported, return None.
    """
    try:
        record = reki.load_catalog(plugins=False, user=False).resolve(system_name).record
    except KeyError:
        return None
    return record.metadata.get("legacy_data_dir")
