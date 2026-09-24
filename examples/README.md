# cemc-plots-kit 示例

任务文件使用 `cemc.plots/v2`；其中产品 ID 指向 cedar-graph workflow，外部 recipe
使用 `cedarkit.plots/v3`。任务 schema 与产品 schema 版本独立。

- [`task-v2-cmadaas-mount.yaml`](task-v2-cmadaas-mount.yaml)：`/CMADAAS` 上的
  CMA-GFS `cn.t2m` 产品。
- [`task-v2-ensemble.yaml`](task-v2-ensemble.yaml)：CMA-GEPS 集合温度，示例成员为
  `m001`、`m002`，control 为 `m000`，并让 control 参与 MAX。
- [`recipes/t2m_custom.yaml`](recipes/t2m_custom.yaml)：外部 v3 温度 recipe。

从 app 仓库根目录验证任务、检查静态计划、解释单项作业并执行：

```bash
cemc-plots validate examples/task-v2-cmadaas-mount.yaml
cemc-plots plan examples/task-v2-cmadaas-mount.yaml
cemc-plots explain examples/task-v2-cmadaas-mount.yaml \
  --plot cn.t2m --forecast-time 24h
cemc-plots run examples/task-v2-cmadaas-mount.yaml
```

前 3 条命令不访问数据或输出目录。`run` 要求本机挂载路径包含对应预报文件，会
写入图像和 `task-manifest.json`。样例日期、系统和成员 ID 应根据现场文件目录修改。
集合产品字段、CLI 行为和生命周期见 [`../docs/task-workflow.md`](../docs/task-workflow.md)。
