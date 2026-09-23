# cemc-plots-kit 任务用例

`task.yaml` 演示 plots 段的三种取值形式与外部配方引用：

* `cn.h_500_psl: on` —— 开关形式
* `cn.rain_wind_10m` —— 参数映射/列表形式（`interval` 参数）
* `recipes/t2m_custom.yaml` —— 外部配方，相对 task 文件目录解析，
  输出文件名为 `t2m_custom_<起报时次>_<时效>.png`

运行：

```shell
python -m cemc_plots_kit task --task-file ./task.yaml
```

外部配方 `recipes/t2m_custom.yaml` 基于内置 v3 `cn.t2m` workflow，
默认使用夏季色标并修改标题。可复制
`cedar_graph/recipes/workflow/cn/t2m.yaml` 后按需修改。
