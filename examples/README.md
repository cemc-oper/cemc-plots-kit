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

外部配方 `recipes/t2m_custom.yaml` 在内置 `cn.t2m` 配方基础上固定使用
夏季色标并修改了标题，演示"不发版即可加图"：复制一份内置配方
（`cedar_graph/recipes/cn/`）按需修改即可。
