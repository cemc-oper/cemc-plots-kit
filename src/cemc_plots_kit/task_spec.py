"""Versioned, side-effect-free task input models."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import reki
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class TaskSpecError(ValueError):
    """A deterministic task input or source-policy failure."""


def _duration(value: Any) -> str:
    try:
        duration = pd.to_timedelta(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("must be a valid duration") from exc
    if pd.isna(duration) or duration < pd.Timedelta(0):
        raise ValueError("must be a non-negative duration")
    return str(duration)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceConfig(StrictModel):
    dataset: str = Field(min_length=1)
    overrides: dict[str, str] = Field(default_factory=dict)

    @field_validator("overrides")
    @classmethod
    def only_storage_base(cls, value: dict[str, str]) -> dict[str, str]:
        unknown = set(value) - {"storage_base"}
        if unknown:
            raise ValueError(f"unsupported source overrides: {', '.join(sorted(unknown))}")
        if "storage_base" in value and not Path(value["storage_base"]).is_absolute():
            raise ValueError("storage_base must be an absolute path")
        return value


class TimeConfigV2(StrictModel):
    start_time: str
    forecast_start: str = "0 days 00:00:00"
    forecast_time: str
    forecast_interval: str

    _forecast_time = field_validator("forecast_time", mode="before")(_duration)
    _forecast_start = field_validator("forecast_start", mode="before")(_duration)
    _forecast_interval = field_validator("forecast_interval", mode="before")(_duration)

    @field_validator("start_time", mode="before")
    @classmethod
    def normalized_start_time(cls, value: str | int) -> str:
        value = str(value)
        if len(value) not in {8, 10, 12} or not value.isdigit():
            raise ValueError("must use YYYYMMDD, YYYYMMDDHH, or YYYYMMDDHHMM")
        try:
            return pd.to_datetime(value, format={8: "%Y%m%d", 10: "%Y%m%d%H", 12: "%Y%m%d%H%M"}[len(value)]).strftime("%Y%m%d%H%M")
        except ValueError as exc:
            raise ValueError("must be a valid timestamp") from exc

    @model_validator(mode="after")
    def interval_not_larger_than_range(self):
        if pd.Timedelta(self.forecast_interval) <= pd.Timedelta(0):
            raise ValueError("forecast_interval must be greater than zero")
        if pd.Timedelta(self.forecast_interval) > pd.Timedelta(self.forecast_time):
            raise ValueError("forecast_interval cannot exceed forecast_time")
        if pd.Timedelta(self.forecast_start) > pd.Timedelta(self.forecast_time):
            raise ValueError("forecast_start cannot exceed forecast_time")
        return self


class RuntimeConfigV2(StrictModel):
    work_dir: Path = Path("work")
    output_dir: Path = Path("output")
    missing: Literal["fail", "skip", "warn"] = "skip"
    workers: int = Field(default=1, ge=1)
    shared_reads: bool = True


class AreaConfigV2(StrictModel):
    start_longitude: float
    end_longitude: float
    start_latitude: float
    end_latitude: float


class PlotTaskV2(StrictModel):
    api_version: Literal["cemc.plots/v2"]
    kind: Literal["PlotTask"]
    source: SourceConfig
    time: TimeConfigV2
    runtime: RuntimeConfigV2 = Field(default_factory=RuntimeConfigV2)
    plots: dict[str, bool | dict[str, Any] | list[dict[str, Any]]] = Field(
        min_length=1,
        description="v3 product ID or external v3 YAML path mapped to parameters; cn.ens_t2m requires member_ids",
    )
    area: AreaConfigV2 | None = None


def mounted_catalog_path() -> Path:
    """Return the deployable example catalog, which deliberately has no mount path."""
    return Path(str(files("cemc_plots_kit").joinpath("catalog/cmadaas_mount.yaml")))


@dataclass(frozen=True)
class ResolvedTaskSource:
    source: dict[str, Any]
    dataset_id: str
    origin: str
    definitions: tuple[dict[str, Any], ...]
    parameters: dict[str, Any]


def resolve_task_source(source: SourceConfig) -> dict[str, Any]:
    """Resolve a mounted source without opening a provider or contacting a service."""
    return resolve_task_dataset(source).source


def resolve_task_dataset(source: SourceConfig):
    """Bind the application's mount aliases to a public local declaration.

    This is static resource validation, with no source construction or data I/O.
    The application owns deployment aliases; reki owns product interpretation.
    """
    import yaml
    from reki.catalog import plan_source_binding
    from reki.catalog.model import thaw

    catalog_path = mounted_catalog_path()
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    declaration = next(
        (dict(row["source"]) for row in catalog["datasets"]
         if source.dataset == row["id"] or source.dataset in row.get("aliases", [])),
        {"kind": "local", "dataset": source.dataset},
    )
    root = source.overrides.get("storage_base")
    if root is None:
        raise TaskSpecError("source policy requires an explicit overrides.storage_base")
    declaration["root"] = root
    try:
        configuration = plan_source_binding(declaration)
    except (reki.QueryError, reki.SourceError) as exc:
        raise TaskSpecError(f"source policy: {exc}") from exc
    return ResolvedTaskSource(
        source=thaw(configuration.source),
        dataset_id=configuration.source["dataset"],
        origin=str(catalog_path),
        definitions=tuple(thaw(item) for item in configuration.definitions),
        parameters=thaw(configuration.parameters or {}),
    )


def load_task_spec(path: Path, *, check_source_policy: bool = True) -> PlotTaskV2:
    """Read and validate one versioned task without accessing field values."""
    import yaml
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TaskSpecError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise TaskSpecError("task document must be a mapping")
    try:
        task = PlotTaskV2.model_validate(raw)
    except ValidationError as exc:
        raise TaskSpecError(exc.json(include_url=False)) from exc
    if check_source_policy:
        resolve_task_source(task.source)
    return task


def write_json_schema(path: Path) -> None:
    """Generate the packaged schema; used by the drift test/release step."""
    import json
    path.write_text(json.dumps(PlotTaskV2.model_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
