# cemc-plots-kit 任务用例

任务文件使用版本化 `cemc.plots/v2` schema。当前示例分别演示 CMADaaS
挂载数据集和集合预报产品：

- `task-v2-cmadaas-mount.yaml`：CMA-GFS 单产品任务。
- `task-v2-ensemble.yaml`：CMA-GEPS 集合温度任务。

先验证或生成静态计划；执行命令会读取任务中配置的数据源：

```shell
cemc-plots validate ./task-v2-cmadaas-mount.yaml
cemc-plots plan ./task-v2-cmadaas-mount.yaml
cemc-plots run ./task-v2-cmadaas-mount.yaml
```

集合示例可用同样的 `validate`、`plan`、`run` 命令，将任务路径替换为
`./task-v2-ensemble.yaml`。
