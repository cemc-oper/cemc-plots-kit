# 任务文件、CLI 与运行生命周期

`cemc-plots-kit` 的任务文件描述本地数据集、预报时次、运行选项和产品选择，
schema 版本为 `cemc.plots/v2`。文件中的产品 ID 选择 cedar-graph workflow 产品；
外部 YAML 配方必须遵循 `cedarkit.plots/v3`。前者是批处理任务契约，后者是单个
绘图产品的数据和展示契约。

正式 task schema 位于包资源 `cemc_plots_kit/schemas/task-v2.json`。任务解析使用
严格字段模型，未知字段会报错；包内数据集 catalog 位于
`cemc_plots_kit/catalog/`，部署机器的挂载路径在任务的 `source.overrides` 中指定。

## 任务结构

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
  workers: 1
  shared_reads: true
plots:
  cn.t2m: true
```

`plots` 中的值可以是 `true`、一组参数映射或参数映射列表。`cn.ens_t2m` 必须
显式传入 `member_ids`，并可分别指定 control、是否纳入 MAX、缺测策略和列数。
外部 recipe 路径按任务 YAML 所在目录解析。任务和 recipe 均不携带用户凭据。

## CLI 命令

```bash
cemc-plots validate examples/task-v2-cmadaas-mount.yaml
cemc-plots plan examples/task-v2-cmadaas-mount.yaml
cemc-plots explain examples/task-v2-cmadaas-mount.yaml \
  --plot cn.t2m --forecast-time 24h
cemc-plots run examples/task-v2-cmadaas-mount.yaml
```

`validate` 解析严格 task schema 并核对 catalog 来源策略。`plan` 编译产品与字段
请求，输出规范化 JSON 计划；`explain` 定位一项产品和预报时次。前三个命令不创建
provider、不解码数据、不渲染、不写输出。`run` 才读取任务文件中配置的数据源，
执行计划并输出 `task-manifest.json`。

## provider、worker 与输出

- `workers: 1` 使用确定性串行执行；大于 1 时使用独立进程运行作业组。
- `shared_reads: true` 在本任务/worker 范围内复用 provider 及字段缓存；设为
  `false` 时每个作业独立创建读取上下文。不同任务不共享可变字段缓存或绘图状态。
- `missing: skip|warn` 只影响明确的缺失数据；配置、编译和其他读取错误不会被当作
  缺失吞掉。manifest 保留每个作业的 success、skipped 或 failed 状态。
- PNG 与 manifest 使用目标目录中的唯一临时文件，成功后原子替换；失败时清理临时
  文件并保留之前已完整写入的结果。
- 完成绘图后关闭任务自己创建的 Panel/provider；不会关闭调用方拥有的 Figure 或
  provider。

本地挂载目录是文件数据源，不会调用 CMADaaS 在线接口。实际 `run` 需要对应系统
的数据文件、可用 ecCodes 运行库和满足 catalog 模板的目录结构；`validate`、`plan`
和 `explain` 无此数据前提。

## 外部产品 recipe

自定义产品 recipe 由 `cedarkit-plots` 的 `cedarkit.plots/v3` loader 加载，静态
plan 与内置产品走同一 workflow 执行链。直接校验/预览 recipe 可使用：

```bash
cedarkit-plots recipe validate examples/recipes/t2m_custom.yaml
cedarkit-plots recipe plan examples/recipes/t2m_custom.yaml \
  --start-time 2024-07-01T00:00Z --forecast-time 24h --format json
```

任务示例及其 CLI 命令见 [`../examples/README.md`](../examples/README.md)。
