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

`time.forecast_start` 可指定起始时效，默认 `0h`；它不得大于 `forecast_time`。
只复跑 +6h 时，设置 `forecast_start: 6h`、`forecast_time: 6h` 和
`forecast_interval: 6h`。首链冻结样例见
[`../examples/task-v2-gfs-t2m.yaml`](../examples/task-v2-gfs-t2m.yaml)。

挂载数据集别名在应用内转换成公共 `local` 来源声明；`source.dataset` 也接受
reki 中已登记的规范产品 ID。绑定时只校验版本化资源，不检查挂载目录和业务文件。
显式文件的 `file + native.grib` 读取是 reki 的独立能力，不要求应用数据集别名登记。

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
- 公共读场异常经过 workflow 包装后，仍按根因分类：`no_match`／`missing_fields`
  可应用缺场策略，解码、服务、权限和歧义错误继续失败。失败记录保留公共错误对象、
  workflow 节点／配方位置及 provider trace。
- 成功作业的 provider trace 包含公共查询报告、字段身份和原文件引用；来源定义
  记录实际资源内容版本及 SHA256，可与候选 wheel 清单共同追溯软件和输入。
- PNG 与 manifest 使用目标目录中的唯一临时文件，成功后原子替换；失败时清理临时
  文件并保留之前已完整写入的结果。
- 完成绘图后关闭任务自己创建的 Panel/provider；不会关闭调用方拥有的 Figure 或
  provider。

## 中断记录与显式恢复

任务开始和每个作业开始／结束时，应用都会原子更新 `task-manifest.json`。
运行中可看到 `running`、已完成结果及尚未执行的作业；正常退出时结算为
`success`、`partial` 或 `failed`。普通作业失败后仍继续后续作业。
单 worker CLI 收到 SIGINT 或 SIGTERM 时记录 `interrupted`，保留已完成结果、活动作业的
中断状态及未执行项，并退出 130。临时 PNG 在可处理的中断中清理。

修复故障后，可对同一任务显式恢复：

```bash
cemc-plots run task.yaml --resume
```

恢复只支持 `workers: 1`，并要求保持同一任务路径和安装环境。应用在写入前核对任务文件摘要、完整编译计划、软件与
资源标识；复用每个成功作业前，还核对原文件指纹和输出 SHA256。任何已成功结果
的输入或输出发生变化都会拒绝恢复，保留原 manifest，避免混合不同来源的图。
失败、缺场跳过、中断和尚未执行的作业会重新尝试。没有 `--resume` 时按原有方式
从头执行；旧版本没有恢复元数据的 manifest 不能用于恢复。

输入指纹检查设备、inode、大小及纳秒级修改／状态变更时间，不是完整原文件的
内容哈希。恢复用于保持原文件不变的本地挂载数据；不是对可任意改写的输入的
内容寻址缓存。该机制不提供多个进程同时写同一输出目录的协调，也不保证 SIGKILL
或断电时执行清理；此类终止只能从最后已发布的 checkpoint 显式重试。
多 worker 中断会等待已运行子进程退出；本批不承诺强制停止子进程或多 worker 恢复。

作业记录包含阶段计时：读场来自 provider trace，计算及运行时开销由执行时间扣除
读场时间得到，绘图构建和保存分别记录；保存包含最终画布绘制及原子发布，不能
当作纯磁盘写入时间。

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

## Ensemble temperature population records

For `cn.ens_t2m`, `member_ids` select perturbations and `control_id` selects the
control. `model` supplies the figure label. Member reads carry explicit roles,
and aliases selecting the same native member are rejected before execution.
`include_control_in_max` controls whether the control contributes to MAX.

The manifest result contains `ensemble` with requested/realized/missing IDs,
control inclusion, `max_input_ids`, requested and realized MAX input counts, and
the minimum/maximum per-grid valid input count. MAX is a pointwise maximum over
the selected inputs, not a probability computed over the full model population.
An absent member under the product's `missing_policy: skip` can produce a valid
partial product; its effective count and missing IDs stay visible. Grid-point
NaNs do not count as valid inputs, and all-missing points remain NaN.

The task-level `runtime.missing` policy still controls missing jobs. Member
absence under the product's `error` policy is classified as `field_missing` with
the read-node cause. Ambiguity, inconsistent identities/grids, a required missing
control and an empty realized member set remain failures; they are not silently
converted into a smaller ensemble.

N09D freezes CMA-GEPS 2026-11-02 12 UTC +24h, control 0 and perturbations 1–3.
The original header declares 31 ensemble forecasts; this selected subset does
not establish a complete 31-member population. Exact candidate installation and
whole-cohort restoration are accepted separately in N10E.
