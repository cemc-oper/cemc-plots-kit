import importlib
import re

from cemc_plots_kit.plots import rain

#: rain_{n}h_wind_10m 系列图名，n 为降水累计小时数
RAIN_PLOT_NAME_PATTERN = re.compile(r"rain_(\d+)h_wind_10m")


def get_plot_module(plot_name: str, module_name: str = "cemc_plots_kit.plots"):
    """
    按图名加载绘图模块。

    ``rain_{n}h_wind_10m`` 系列由参数化的 ``rain`` 模块构造，
    其余图名按模块路径动态导入。
    """
    m = RAIN_PLOT_NAME_PATTERN.fullmatch(plot_name)
    if m is not None:
        return rain.create_plot_module(interval_hours=int(m.group(1)))
    plot_module = importlib.import_module(f"{module_name}.{plot_name}")
    return plot_module
