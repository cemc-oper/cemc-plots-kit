"""plot_type 解析与输出命名测试（cemc_plots_kit.plots）。"""
import types

import pandas as pd
import pytest

from cemc_plots_kit.config import PlotConfig, TimeConfig
from cemc_plots_kit.plots import (
    check_plot_available,
    get_plot_definition,
    get_plot_label,
    is_recipe_path,
)


class TestIsRecipePath:
    def test_yaml_suffix(self):
        assert is_recipe_path("recipes/t2m_custom.yaml") is True
        assert is_recipe_path("/abs/path/t2m.yml") is True

    def test_plot_type_is_not_path(self):
        assert is_recipe_path("cn.t2m") is False
        assert is_recipe_path("cn.shr.default") is False


class TestGetPlotLabel:
    def test_plot_type_dots_to_underscores(self):
        assert get_plot_label("cn.t2m") == "cn_t2m"
        assert get_plot_label("cn.shr.default") == "cn_shr_default"

    def test_recipe_path_uses_stem(self):
        assert get_plot_label("recipes/t2m_custom.yaml") == "t2m_custom"
        assert get_plot_label("/abs/path/my_plot.yml") == "my_plot"

    def test_params_suffix_sorted(self):
        assert get_plot_label("cn.rain_wind_10m", {"interval": "3h"}) == "cn_rain_wind_10m_interval_3h"
        assert (
            get_plot_label("cn.kidx_wind", {"wind_level": 850, "area_name": "X"})
            == "cn_kidx_wind_area_name_X_wind_level_850"
        )

    def test_empty_params_no_suffix(self):
        assert get_plot_label("cn.t2m", {}) == "cn_t2m"


class TestGetPlotDefinition:
    def test_recipe_plot_type(self):
        definition = get_plot_definition("cn.t2m")
        for attr in ("PlotMetadata", "PlotData", "load_data", "plot", "check_available"):
            assert hasattr(definition, attr), attr

    def test_python_module_plot_type(self):
        """诊断复杂图形保留 Python 逃生舱（设计文档 D6）。"""
        definition = get_plot_definition("cn.shr.default")
        assert isinstance(definition, types.ModuleType)
        for attr in ("PlotMetadata", "load_data", "plot"):
            assert hasattr(definition, attr), attr

    def test_external_recipe_path(self, tmp_path):
        recipe_path = tmp_path / "recipes" / "t2m_custom.yaml"
        recipe_path.parent.mkdir()
        recipe_path.write_text(EXTERNAL_RECIPE, encoding="utf-8")

        # 相对路径基于 base_dir 解析
        definition = get_plot_definition("recipes/t2m_custom.yaml", base_dir=tmp_path)
        assert definition.recipe.name == "custom 2m temperature"

        # 绝对路径直接加载
        definition = get_plot_definition(str(recipe_path))
        assert definition.recipe.name == "custom 2m temperature"

    def test_unknown_plot_type_raises(self):
        with pytest.raises(Exception):
            get_plot_definition("cn.no_such_plot")


class TestCheckPlotAvailable:
    """配方 check_available 由引擎默认实现；未提供的定义视为可用。"""

    @staticmethod
    def _time_config(hours: int) -> TimeConfig:
        return TimeConfig(
            start_time=pd.Timestamp("2024-07-01 00:00"),
            forecast_time=pd.Timedelta(hours=hours),
        )

    def test_recipe_without_time_diff_always_available(self):
        definition = get_plot_definition("cn.t2m")
        assert check_plot_available(definition, self._time_config(0), PlotConfig("cn.t2m")) is True

    def test_recipe_with_static_interval(self):
        """cn.rain_24h：time_diff 24h，0h 时效不可用。"""
        definition = get_plot_definition("cn.rain_24h")
        assert check_plot_available(definition, self._time_config(0), PlotConfig("cn.rain_24h")) is False
        assert check_plot_available(definition, self._time_config(24), PlotConfig("cn.rain_24h")) is True

    def test_recipe_with_param_interval(self):
        """cn.rain_wind_10m：interval 由 plot_params 提供。"""
        definition = get_plot_definition("cn.rain_wind_10m")
        plot_config = PlotConfig("cn.rain_wind_10m", plot_params={"interval": "3h"})
        assert check_plot_available(definition, self._time_config(1), plot_config) is False
        assert check_plot_available(definition, self._time_config(3), plot_config) is True

    def test_module_without_check_available(self):
        definition = get_plot_definition("cn.shr.default")
        assert check_plot_available(definition, self._time_config(0), PlotConfig("cn.shr.default")) is True


#: 与 cedar_graph.recipes.cn.t2m 等价的简化外部配方（季节 select 固定夏季）
EXTERNAL_RECIPE = """
name: "custom 2m temperature"
domain: { default: east_asia, area: cn_area }

data:
  t2m:
    field: t2m
    transforms:
      - { op: style_units }

layers:
  - field: t2m
    style: t2m:cn_summer

title: { graph_name: "2m Temperature (C)" }
colorbar: { layer: 0 }
"""
