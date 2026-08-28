# cemc-plots-kit

A plotting tool for Numerical Weather Prediction model data of CEMC.

cemc-plots-kit 只包含业务编排逻辑（CLI / 配置 / 任务 / 数据源）；图形本身由
[cedar-graph](https://github.com/cemc-oper/cedar-graph) 的**配方**（YAML）或
Python 图形模块实现，`plot_type` 直接映射，无需逐图包装代码。

## Install

Download the latest source code from GitHub and install manually.

## Getting started

### Single plot

Draw a single figure in command line.

The following command draws a figure for 2m temperature using CMA-GFS data in CMA-HPC.

```shell
python -m cemc_plots_kit draw \
  --system-name cma_gfs \
  --plot-type cn.t2m \
  --start-time 2024111300 \
  --forecast-time 24h \
  --work-dir .
```

The command will generate an image file named `cn_t2m_2024111300_024.png` in current directory.

`--plot-type` 取值：

* cedar-graph 配方，如 `cn.t2m`、`cn.h_500_psl`、`cn.rain_24h`（见下表）
* cedar-graph Python 图形模块（诊断复杂图形），如 `cn.shr.default`、`cn.t_dew_t.default`
* 外部配方文件路径（`.yaml`/`.yml`），见"外部配方"一节

内置配方（`cn.` 前缀）：

| plot_type | 图形 |
|---|---|
| `cn.t2m` | 2 米温度 |
| `cn.rh2m` | 2 米相对湿度 |
| `cn.h_500_psl` | 500 hPa 高度场 + 海平面气压 |
| `cn.h_500_wind_850` | 500 hPa 高度场 + 850 hPa 风 |
| `cn.kidx_wind` | K 指数 + 风（需 `wind_level` 参数） |
| `cn.bli_wind` / `cn.cape_wind` / `cn.cin_wind` | 对流指数 + 风（需 `wind_level` 参数） |
| `cn.cdbz` | 组合反射率 |
| `cn.wind_10m` | 10 米风 |
| `cn.rain_24h` | 24 小时累计降水 |
| `cn.rain_wind_10m` | 间隔累计降水 + 10 米风（需 `interval` 参数） |
| `cn.prep_24h` | 24 小时降水相态（雨/雨夹雪/雪） |

### Batch plot

Draw a batch of figures using a task file.

Create a task file named `task.yaml` with content:

```yaml
runtime:
  base_work_dir: .

# Use catalog defaults.  CMA-GFS is bound to its canonical local dataset.
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

`source: {}` 使用 catalog 的默认绑定。旧 task 的显式目录和文件名写法仍然支持，且优先于 catalog：

```yaml
source:
  data_dir: /g3/COMMONDATA/OPER/CEMC/GFS_GMF/Prod-grib/{start_time_label}/ORIG
  data_file_name_template: gmf.gra.{start_time_label}{forecast_hour_label}.grb2
```

相对 `data_dir` 以 task 文件所在目录为基准。运行时会把这对 v1 字段转换为受限的 `file-pattern` source；图题和输出文件名继续使用原有的 `system_name`。

Execute the following shell command to draw figures:

```shell
python -m cemc_plots_kit task --task-file ./task.yaml
```

When the command is executed, there are 14 image files in output directory:

```text
cn_h_500_psl_2024111300_000.png
cn_h_500_psl_2024111300_006.png
cn_h_500_psl_2024111300_012.png
cn_h_500_psl_2024111300_018.png
cn_h_500_psl_2024111300_024.png
cn_h_500_psl_2024111300_030.png
cn_h_500_psl_2024111300_036.png
cn_h_500_psl_2024111300_042.png
cn_h_500_psl_2024111300_048.png
cn_rain_24h_2024111300_024.png
cn_rain_24h_2024111300_030.png
cn_rain_24h_2024111300_036.png
cn_rain_24h_2024111300_042.png
cn_rain_24h_2024111300_048.png
```

注意 `cn.rain_24h` 需要 24 小时累计场，0h 时效由配方的 `check_available`
默认实现自动过滤。

### plots 段格式

`plots` 段的每个键是一个 plot_type（或外部配方路径），值支持三种形式：

```yaml
plots:
  # 1. 开关：on/off，无参数
  cn.t2m: on

  # 2. 参数映射：传递给配方参数
  cn.rain_wind_10m:
    interval: 3h

  # 3. 参数列表：同一图形出多组参数（如多个降水时段）
  cn.rain_wind_10m:
    - { interval: 1h }
    - { interval: 3h }
```

带参数的输出文件/目录名会追加参数后缀，如
`cn_rain_wind_10m_interval_3h_2024111300_024.png`。

### 外部配方

`plots` 段的键为 `.yaml`/`.yml` 路径时，按外部配方文件加载——
不等待 cedar-graph 发版即可增加新图形。相对路径基于 task 文件所在目录解析，
输出文件名取配方文件的 stem：

```yaml
plots:
  cn.t2m: on
  recipes/t2m_custom.yaml: on        # 相对 task 文件目录
  /data/opr/recipes/my_plot.yaml: on # 绝对路径
```

配方语法见 cedar-graph 的配方编写文档（`cedar_graph/recipes/cn/` 下的
内置配方可作为示例）。`draw` 命令的 `--plot-type` 同样接受配方路径：

```shell
python -m cemc_plots_kit draw \
  --system-name cma_gfs \
  --plot-type ./recipes/t2m_custom.yaml \
  --start-time 2024111300 \
  --forecast-time 24h \
  --work-dir .
```

完整用例见 [examples/](./examples) 目录。

## LICENSE

Copyright &copy; 2024, developers at cemc-oper.

`cemc-plots-kit` is licensed under [Apache License V2.0](./LICENSE)
