"""
plot_type → 图形定义解析。

``plot_type`` 选择 cedar-graph 的 v3 产品，或加载外部 v3 YAML recipe。
静态计划与动态执行使用同一个产品定义。
"""
from pathlib import Path
from typing import Optional, Union

from cedar_graph.recipes.ensemble_product import EnsembleRequest, EnsembleT2MProduct, select_ensemble_product
from cedar_graph.recipes.workflow_product import WorkflowProduct, load_workflow_product, select_workflow_product
from cedarkit.plots.workflow.plan import CompileContext, RecipeCompileError

from cemc_plots_kit.config import PlotConfig, TimeConfig

#: 外部配方文件后缀
RECIPE_FILE_SUFFIXES = (".yaml", ".yml")


def is_recipe_path(plot_name: str) -> bool:
    """plot_name 是否为外部配方文件路径。"""
    return plot_name.lower().endswith(RECIPE_FILE_SUFFIXES)


def get_plot_definition(plot_name: str, base_dir: Optional[Union[str, Path]] = None):
    """
    按 plot_type 解析 v3 产品定义。

    Parameters
    ----------
    plot_name
        cedar-graph 产品（如 ``cn.t2m``、``cn.shr.default``、``cn.ens_t2m``），
        或外部 v3 配方文件路径（相对路径基于
        ``base_dir`` 解析）。
    base_dir
        相对配方路径的基准目录，通常为 task 文件所在目录。

    Returns
    -------
    v3 workflow 或集合产品对象。
    """
    selected = select_ensemble_product(plot_name) or select_workflow_product(plot_name)
    if selected is not None:
        return selected

    if is_recipe_path(plot_name):
        recipe_path = Path(plot_name)
        if not recipe_path.is_absolute():
            recipe_path = Path(base_dir if base_dir is not None else ".") / recipe_path
        return load_workflow_product(recipe_path)

    raise KeyError(f"unknown v3 product {plot_name!r}")


def check_plot_available(plot_definition, time_config: TimeConfig, plot_config: PlotConfig) -> bool:
    """
    调用图形定义的 ``check_available`` 过滤无效时次组合。

    Workflow 编译时检查时效约束；集合参数静态验证。
    """
    if isinstance(plot_definition, EnsembleT2MProduct):
        EnsembleRequest.from_params(plot_config.plot_params)
        return True
    if isinstance(plot_definition, WorkflowProduct):
        try:
            plot_definition.compile(workflow_context(time_config, plot_config))
        except RecipeCompileError as exc:
            if exc.code == "planner" and "time_diff interval" in str(exc):
                return False
            raise
        return True
    raise TypeError("plot definition must be a v3 product")


def workflow_context(time_config: TimeConfig, plot_config: PlotConfig) -> CompileContext:
    params = dict(plot_config.plot_params)
    if plot_config.plot_name == "cn.pte_wind.default" and "pte_levels" in params:
        levels = params.pop("pte_levels")
        if not isinstance(levels, (list, tuple)) or len(levels) != 2:
            raise ValueError("pte_levels must contain two pressure levels")
        params.setdefault("pte_first_level", levels[0])
        params.setdefault("pte_second_level", levels[1])
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
        def label_value(value):
            return "-".join(map(str, value)) if isinstance(value, (list, tuple)) else str(value)
        suffix = "_".join(f"{key}_{label_value(value)}" for key, value in sorted(plot_params.items()))
        label = f"{label}_{suffix}"
    return label
