# cemc-plots-kit

`cemc-plots-kit` 是面向 CEMC 数值预报业务绘图任务的命令行工具。它负责
任务配置、数据源选择、时间调度、并发执行和产物管理；具体的业务图种由
[cedar-graph](https://github.com/cemc-oper/cedar-graph) 提供，底层绘制由
`cedarkit-plots` 完成。

当前开发版变更见 [CHANGELOG.md](CHANGELOG.md)。

任务中的图种 ID 选择 cedar-graph workflow 产品；外部 YAML 路径必须是
`cedarkit.plots/v3` workflow recipe。产品编译、provider 请求和绘图都经过同一条
新链，不再加载独立 Python `load_data`/`plot` 模块。

注意两个版本字段描述不同对象：任务文件使用 `cemc.plots/v2`，其内部引用的产品
配方使用 `cedarkit.plots/v3`。这两个版本号互不对应，也不能互换。

## 适用场景

- 从 `/CMADAAS` 等 CMADaaS 挂载目录批量生成业务预报图；
- 按起报时间、预报时效和间隔调度多个图种；
- 在同一任务中使用内置图种与本地自定义 YAML 配方；
- 预先校验、查看和解释任务计划，再执行实际绘图；
- 生成可追溯的 `task-manifest.json`，记录任务和每个作业的结果。

> 当前项目处于 Sandbox 阶段，任务规范、公共接口和支持的图种仍可能演进。

## 安装

要求 Python 3.11 或更高版本。使用 `uv` 安装命令行工具：

```shell
uv tool install cemc-plots-kit
```

在本开发工作区中进行开发和测试：

```shell
cd app/cemc-plots-kit
uv sync --extra test
pytest
```

读取真实 GRIB2 数据还需要系统已安装 ecCodes，并且运行环境能够访问
CMADaaS 挂载目录。

## 快速开始：运行 CMADaaS 挂载目录任务

项目提供了可部署的 `cemc.plots/v2` 任务模板
[`examples/task-v2-cmadaas-mount.yaml`](examples/task-v2-cmadaas-mount.yaml)。
它使用内置的 CMADaaS 挂载目录数据集，并将机器相关的挂载点保留在任务文件中：

```yaml
api_version: cemc.plots/v2
kind: PlotTask

source:
  dataset: cma_gfs_gmf_cmadaas_mount
  overrides:
    storage_base: /CMADAAS

time:
  start_time: 2026092200
  forecast_time: 24h
  forecast_interval: 24h

runtime:
  work_dir: ./work
  output_dir: ./output
  missing: skip

plots:
  cn.t2m: true
```

先执行不会读取数据或写入文件的检查命令：

```shell
cemc-plots validate examples/task-v2-cmadaas-mount.yaml
cemc-plots plan examples/task-v2-cmadaas-mount.yaml
cemc-plots explain examples/task-v2-cmadaas-mount.yaml \
  --plot cn.t2m --forecast-time 24h
```

确认计划无误后执行绘图：

```shell
cemc-plots run examples/task-v2-cmadaas-mount.yaml
```

`validate`、`plan` 和 `explain` 是离线操作：不会创建数据 reader、读取或解码
数据、请求 CMADaaS 服务、渲染图形或写入输出。`run` 会在 `output_dir` 中原子地
写入图像与 `task-manifest.json`。

字段含义、参数形式、manifest 状态以及 worker/provider 生命周期见
[`docs/task-workflow.md`](docs/task-workflow.md)。

CMADaaS 挂载目录属于本地文件数据源，而非 CMADaaS 在线服务；上述用法不需要
CMADaaS 服务凭据。挂载目录布局需与 reki 中对应系统的 `cmadaas` 路径模板一致。

## 数据源

包内 catalog 已提供以下挂载目录数据集：

| 数据集 ID | 别名 | 适用系统 |
| --- | --- | --- |
| `cma_gfs_gmf_cmadaas_mount` | `CMA-GFS-CMADAAS-MOUNT` | CMA-GFS |
| `cma_meso_3km_cmadaas_mount` | `CMA-MESO-3KM-CMADAAS-MOUNT` | CMA-MESO 3 km |
| `cma_tym_cmadaas_mount` | `CMA-TYM-CMADAAS-MOUNT` | CMA-TYM |
| `cma_geps_perturbation_cmadaas_mount` | `CMA-GEPS-PERTURBATION-CMADAAS-MOUNT` | CMA-GEPS 扰动成员 |

在任务的 `source.dataset` 中选择数据集，并通过
`source.overrides.storage_base` 指定当前机器的挂载根目录。不要把特定机器的
挂载路径写入包内 catalog。

## 图种与参数

`plots` 的每个键可以是内置图种名，也可以是外部 `.yaml` / `.yml` 配方路径。
值可使用以下三种形式：

```yaml
plots:
  # 无参数图种
  cn.t2m: true

  # 一组图种参数
  cn.rain_wind_10m:
    interval: 3h

  # 同一图种生成多组参数结果
  cn.rain_wind_10m:
    - { interval: 1h }
    - { interval: 3h }

  # 外部配方；相对路径以任务文件所在目录为基准
  recipes/t2m_custom.yaml: true
```

常用内置图种包括：

| `plot_type` | 产品 |
| --- | --- |
| `cn.t2m` | 2 米气温 |
| `cn.rh2m` | 2 米相对湿度 |
| `cn.h_500_psl` | 500 hPa 位势高度与海平面气压 |
| `cn.h_500_wind_850` | 500 hPa 位势高度与 850 hPa 风场 |
| `cn.wind_10m` | 10 米风场 |
| `cn.rain_24h` | 24 小时累计降水 |
| `cn.rain_wind_10m` | 分时段降水与 10 米风场，需 `interval` 参数 |
| `cn.prep_24h` | 24 小时降水相态 |
| `cn.kidx_wind`、`cn.bli_wind`、`cn.cape_wind`、`cn.cin_wind` | 对流指数与风场，需 `wind_level` 参数 |

诊断产品也以 workflow 产品 ID 提供，例如 `cn.shr.default` 和
`cn.t_dew_t.default`。产品 ID 与 v3 配方目录见 cedar-graph 文档。

## 运行行为与产物

- `runtime.workers: 1` 是确定性的参考执行方式；大于 1 时，各 worker 使用
  独立进程和数据 provider。
- `runtime.shared_reads: true` 会在单个任务内共享数据 provider；设为 `false`
  可改为每个作业独立读取。
- `runtime.missing: skip` 会跳过不可用数据对应的作业。例如 24 小时累计降水在
  0 小时时效通常不可用。
- 输出文件会按图种、参数、起报时间和时效命名；参数化图种的名称包含参数后缀。
- `task-manifest.json` 记录任务计划标识、作业结果、数据源标识和任务级共享读取
  统计，但不会记录凭据或完整环境变量值。

## 外部 v3 配方与示例

外部配方可让业务开发在不等待 cedar-graph 发布新版本的情况下新增或修改图种。
复制 `cedar_graph/recipes/workflow/cn/` 中的 v3 配方后按需修改，再在任务文件的 `plots`
中引用即可。相对路径以任务文件所在目录为基准。仓库中的 [examples/](examples/) 包含任务文件和
[`recipes/t2m_custom.yaml`](examples/recipes/t2m_custom.yaml) 示例。

## 许可证

Copyright &copy; 2024-2026, developers at cemc-oper.

`cemc-plots-kit` 采用 [Apache License 2.0](LICENSE)。
