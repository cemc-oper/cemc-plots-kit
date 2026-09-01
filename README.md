# cemc-plots-kit

`cemc-plots-kit` is a command-line orchestration tool for producing graphics
from CEMC numerical weather prediction (NWP) data. It owns task configuration,
data-source selection, scheduling, and output management. Rendering is provided
by [cedar-graph](https://github.com/cemc-oper/cedar-graph), using either
packaged YAML recipes or Python plot modules.

`plot_type` maps directly to a cedar-graph recipe or module; no per-plot wrapper
code is required.

## Requirements and installation

Python 3.11 or later is required. Install the package from PyPI:

```shell
uv tool install cemc-plots-kit
```

For development, install the repository and its test dependencies:

```shell
uv sync --extra test
```

## Quick start: draw one plot

The following command renders a 2 m temperature plot from CMA-GFS data on
CMA-HPC:

```shell
cemc-plots draw \
  --system-name cma_gfs \
  --plot-type cn.t2m \
  --start-time 2024111300 \
  --forecast-time 24h \
  --work-dir .
```

It creates `cn_t2m_2024111300_024.png` in the working directory.

`--plot-type` accepts:

- A packaged cedar-graph recipe, such as `cn.t2m`, `cn.h_500_psl`, or
  `cn.rain_24h`.
- A cedar-graph Python plot module for more complex diagnostic products, such
  as `cn.shr.default` or `cn.t_dew_t.default`.
- A path to an external `.yaml` or `.yml` recipe.

## Packaged recipes

The following recipes use the `cn.` namespace:

| `plot_type` | Product |
| --- | --- |
| `cn.t2m` | 2 m temperature |
| `cn.rh2m` | 2 m relative humidity |
| `cn.h_500_psl` | 500 hPa geopotential height and mean sea-level pressure |
| `cn.h_500_wind_850` | 500 hPa geopotential height and 850 hPa wind |
| `cn.kidx_wind` | K index and wind; requires `wind_level` |
| `cn.bli_wind`, `cn.cape_wind`, `cn.cin_wind` | Convective index and wind; require `wind_level` |
| `cn.cdbz` | Composite reflectivity |
| `cn.wind_10m` | 10 m wind |
| `cn.rain_24h` | 24-hour accumulated precipitation |
| `cn.rain_wind_10m` | Interval precipitation and 10 m wind; requires `interval` |
| `cn.prep_24h` | 24-hour precipitation type (rain, sleet, and snow) |

## Run a task

A task file defines a time range, data source, plots, and runtime behavior.
Create `task.yaml`:

```yaml
runtime:
  base_work_dir: .

# Use catalog defaults. CMA-GFS resolves to its canonical local dataset.
source: {}

system_name: CMA-GFS

time:
  start_time: 2024111300
  forecast_time: 48h
  forecast_interval: 6h

plots:
  cn.h_500_psl: on
  cn.rain_24h: on
```

Run it with:

```shell
cemc-plots task --task-file ./task.yaml
```

This example produces height-and-pressure plots for forecast hours 0 through
48, and precipitation plots for forecast hours 24 through 48. The default
availability check excludes `cn.rain_24h` at forecast hour 0 because a 24-hour
accumulation is not available then.

## Plot configuration

Each key in `plots` is a plot type or an external recipe path. Its value can be
one of the following forms:

```yaml
plots:
  # Enable a plot without parameters.
  cn.t2m: on

  # Pass one parameter mapping to a recipe.
  cn.rain_wind_10m:
    interval: 3h

  # Render the same plot with several parameter mappings.
  cn.rain_wind_10m:
    - { interval: 1h }
    - { interval: 3h }
```

Parameterized output names include a parameter suffix, for example
`cn_rain_wind_10m_interval_3h_2024111300_024.png`.

## Data-source selection

For current tasks, use `source.dataset` to select a local mounted CMADaaS
catalog entry. A v2 task keeps only stable parameter IDs, `FieldQuery` values,
and time semantics in its Recipe or PlotPlan. It never stores service endpoints
or credentials.

The deployment template is
[`examples/task-v2-cmadaas-mount.yaml`](./examples/task-v2-cmadaas-mount.yaml).
Its `storage_base` is task-local, while the packaged catalog contains no
machine-specific mount paths:

```shell
cemc-plots validate examples/task-v2-cmadaas-mount.yaml
cemc-plots plan examples/task-v2-cmadaas-mount.yaml
cemc-plots explain examples/task-v2-cmadaas-mount.yaml \
  --plot cn.t2m --forecast-time 24h
cemc-plots run examples/task-v2-cmadaas-mount.yaml
```

`validate`, `plan`, and `explain` are offline operations: they do not create a
reader, decode data, make a CMADaaS request, render a figure, or write output.
`run` writes figures and `task-manifest.json` atomically to the configured
output directory. The manifest records task-plan identity, each job result,
source identity, and task-local sharing counters; it intentionally excludes
credentials and complete environment-variable values.

Legacy v1 task bindings remain supported. `system_name` or an explicit `source`
selects the dataset at the task layer. Explicit legacy directories and file-name
templates take precedence over catalog defaults:

```yaml
source:
  data_dir: /g3/COMMONDATA/OPER/CEMC/GFS_GMF/Prod-grib/{start_time_label}/ORIG
  data_file_name_template: gmf.gra.{start_time_label}{forecast_hour_label}.grb2
```

A relative `data_dir` is resolved from the directory containing the task file.
At runtime, these v1 fields are converted to a constrained `file-pattern`
source. Existing `system_name` values continue to determine titles and output
file names.

## Runtime behavior

`runtime.workers: 1` is the deterministic reference executor. With
`runtime.shared_reads: true`, it keeps a task-local shared provider. Values
greater than one use isolated processes, so each worker recreates its provider
and file handles. Manifest entries remain in TaskPlan order even when work
completes in a different order. Set `shared_reads: false` to compare against
independent per-job reads.

## External recipes

Use a `.yaml` or `.yml` path as a `plots` key to load an external recipe. This
lets you add a product without waiting for a cedar-graph release. Relative paths
are resolved from the task-file directory, and the output filename uses the
recipe filename stem:

```yaml
plots:
  cn.t2m: on
  recipes/t2m_custom.yaml: on        # Relative to the task-file directory.
  /data/opr/recipes/my_plot.yaml: on # Absolute path.
```

`draw --plot-type` also accepts a recipe path:

```shell
cemc-plots draw \
  --system-name cma_gfs \
  --plot-type ./recipes/t2m_custom.yaml \
  --start-time 2024111300 \
  --forecast-time 24h \
  --work-dir .
```

Refer to the cedar-graph recipe authoring documentation and its packaged
`cedar_graph/recipes/cn/` recipes for syntax and examples. More complete task
examples are available in [examples/](./examples).

## License

Copyright &copy; 2024-2026, developers at cemc-oper.

`cemc-plots-kit` is licensed under the [Apache License 2.0](./LICENSE).
