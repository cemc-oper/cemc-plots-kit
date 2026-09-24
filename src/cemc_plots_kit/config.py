from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Union

import pandas as pd
import reki


from cedarkit.plots.types import AreaRange


@dataclass
class ExprConfig:
    """Data binding shared by every product in one task."""

    area: Optional[AreaRange] = None
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
