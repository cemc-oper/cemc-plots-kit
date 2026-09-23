"""
plot_type → 图形定义解析。

cemc-plots-kit 不携带逐图代码：``plot_type`` 直接映射 cedar-graph 的
配方（YAML）或 Python 图形模块（诊断复杂图形的逃生舱）；键为
``.yaml``/``.yml`` 路径时按外部配方文件加载（不发版即可加图）。

图形定义对象提供统一接口：``PlotMetadata`` / ``load_data`` / ``plot``，
可选 ``check_available``（配方由绘图引擎提供默认实现，Python 模块可
自定义；未提供时视为任意时次组合可用）。
"""
from pathlib import Path
from typing import Optional, Union

from cedar_graph.quickplot import BASE_MODULE_NAME, BASE_RECIPE_NAME
from cedar_graph.recipes.workflow_product import WorkflowProduct, select_workflow_product
from cedarkit.plots.workflow.plan import CompileContext

from cemc_plots_kit.config import PlotConfig, TimeConfig

#: 外部配方文件后缀
RECIPE_FILE_SUFFIXES = (".yaml", ".yml")


def is_recipe_path(plot_name: str) -> bool:
    """plot_name 是否为外部配方文件路径。"""
    return plot_name.lower().endswith(RECIPE_FILE_SUFFIXES)


def get_plot_definition(plot_name: str, base_dir: Optional[Union[str, Path]] = None):
    """
    按 plot_type 解析图形定义（配方适配器或 Python 模块）。

    Parameters
    ----------
    plot_name
        cedar-graph 图形类型（配方如 ``cn.t2m``，Python 模块如
        ``cn.shr.default``），或外部配方文件路径（相对路径基于
        ``base_dir`` 解析）。
    base_dir
        相对配方路径的基准目录，通常为 task 文件所在目录。

    Returns
    -------
    图形定义对象（``PlotMetadata`` / ``load_data`` / ``plot`` /
    可选 ``check_available``）。
    """
    selected = select_workflow_product(plot_name)
    if selected is not None:
        return selected

    from cedar_graph.recipes.engine import get_recipe_engine
    from cedarkit.plots.engine.loader import get_plot_definition as load_definition

    engine = get_recipe_engine()
    if is_recipe_path(plot_name):
        recipe_path = Path(plot_name)
        if not recipe_path.is_absolute():
            recipe_path = Path(base_dir if base_dir is not None else ".") / recipe_path
        return engine.build_module(engine.load_recipe(recipe_path))
    return load_definition(
        plot_type=plot_name,
        base_module_name=BASE_MODULE_NAME,
        recipe_base_module=BASE_RECIPE_NAME,
        engine=engine,
    )


def check_plot_available(plot_definition, time_config: TimeConfig, plot_config: PlotConfig) -> bool:
    """
    调用图形定义的 ``check_available`` 过滤无效时次组合。

    配方由引擎默认实现（``time_diff`` 要求 ``forecast_time >= interval``）；
    定义未提供 ``check_available`` 时视为可用。
    """
    if isinstance(plot_definition, WorkflowProduct):
        plot_definition.compile(workflow_context(time_config, plot_config))
        return True
    check = getattr(plot_definition, "check_available", None)
    if check is None:
        return True
    return check(time_config=time_config, plot_config=plot_config)


def workflow_context(time_config: TimeConfig, plot_config: PlotConfig) -> CompileContext:
    params = dict(plot_config.plot_params)
    if plot_config.plot_name == "cn.t2m" and "style_variant" not in params:
        params["style_variant"] = "cn_summer" if 5 <= time_config.start_time.month <= 9 else "cn_winter"
    return CompileContext(start_time=time_config.start_time, forecast_time=time_config.forecast_time,
                          params=params)


def get_plot_label(plot_name: str, plot_params: Optional[dict] = None) -> str:
    """
    输出命名标签，用于工作目录与输出文件名。

    * 外部配方路径 → 文件 stem（``recipes/t2m_custom.yaml`` → ``t2m_custom``）
    * 图形类型 → 点号替换为下划线（``cn.t2m`` → ``cn_t2m``）
    * 带参数 → 按 key 排序追加 ``_key_value`` 后缀
      （``cn.rain_wind_10m`` + ``{interval: 3h}`` →
      ``cn_rain_wind_10m_interval_3h``）
    """
    if is_recipe_path(plot_name):
        label = Path(plot_name).stem
    else:
        label = plot_name.replace(".", "_")
    if plot_params:
        suffix = "_".join(f"{key}_{value}" for key, value in sorted(plot_params.items()))
        label = f"{label}_{suffix}"
    return label
