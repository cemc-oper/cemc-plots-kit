"""plot_type 解析与输出命名测试（cemc_plots_kit.plots）。"""
import pandas as pd
import pytest

from cemc_plots_kit.config import PlotConfig, TimeConfig
from cemc_plots_kit.plots import (
    EnsembleT2MProduct,
    WorkflowProduct,
    check_plot_available,
    get_plot_definition,
    get_plot_label,
    is_recipe_path,
    workflow_context,
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
        assert get_plot_label("cn.ens_t2m", {"member_ids": ["m01", "m02"]}) == "cn_ens_t2m_member_ids_m01-m02"

    def test_empty_params_no_suffix(self):
        assert get_plot_label("cn.t2m", {}) == "cn_t2m"


class TestGetPlotDefinition:
    def test_recipe_plot_type(self):
        definition = get_plot_definition("cn.t2m")
        assert isinstance(definition, WorkflowProduct)
        assert definition.recipe.recipe.metadata.name == "cn.t2m"
        assert definition.recipe.recipe.api_version == "cedarkit.plots/v3"

    @pytest.mark.parametrize("name", (
        "bli_wind", "cape_wind", "cdbz", "cin_wind", "h_500_psl", "h_500_wind_850",
        "kidx_wind", "prep_24h", "rain_24h", "rain_wind_10m", "rh2m", "t2m", "wind_10m",
    ))
    def test_all_cn_recipes_select_v3_product(self, name):
        definition = get_plot_definition(f"cn.{name}")
        assert isinstance(definition, WorkflowProduct)
        assert definition.recipe.recipe.metadata.name == f"cn.{name}"

    def test_t2m_style_follows_start_month(self):
        product = get_plot_definition("cn.t2m")
        summer = product.compile(workflow_context(
            TimeConfig(pd.Timestamp("2024-07-01"), pd.Timedelta("24h")), PlotConfig("cn.t2m")))
        winter = product.compile(workflow_context(
            TimeConfig(pd.Timestamp("2024-01-01"), pd.Timedelta("24h")), PlotConfig("cn.t2m")))
        assert summer.content.charts[0].plots[0].style == "cemc.t2m:cn_summer"
        assert winter.content.charts[0].plots[0].style == "cemc.t2m:cn_winter"

    def test_ensemble_product_selection(self):
        assert isinstance(get_plot_definition("cn.ens_t2m"), EnsembleT2MProduct)

    @pytest.mark.parametrize("name", ("div_wind", "pte_wind", "qv_div", "shr", "t_dew_t"))
    def test_former_python_product_selects_v3(self, name):
        definition = get_plot_definition(f"cn.{name}.default")
        assert isinstance(definition, WorkflowProduct)
        assert definition.recipe.recipe.metadata.name == f"cn.{name}.default"

    def test_pte_legacy_level_pair_maps_to_explicit_v3_parameters(self):
        product = get_plot_definition("cn.pte_wind.default")
        context = workflow_context(
            TimeConfig(pd.Timestamp("2024-07-01"), pd.Timedelta("24h")),
            PlotConfig("cn.pte_wind.default", plot_params={"wind_level": 850, "pte_levels": (500, 700)}),
        )
        plan = product.compile(context)
        assert plan.content.charts[0].titles[0].text.startswith("PTE 500.0-700.0hPa")
        assert plan.read_count == 4

    def test_external_recipe_path(self, tmp_path):
        recipe_path = tmp_path / "recipes" / "t2m_custom.yaml"
        recipe_path.parent.mkdir()
        recipe_path.write_text(EXTERNAL_RECIPE, encoding="utf-8")

        # 相对路径基于 base_dir 解析
        definition = get_plot_definition("recipes/t2m_custom.yaml", base_dir=tmp_path)
        assert isinstance(definition, WorkflowProduct)
        assert definition.recipe.recipe.metadata.title == "custom 2m temperature"

        # 绝对路径直接加载
        definition = get_plot_definition(str(recipe_path))
        assert isinstance(definition, WorkflowProduct)
        assert definition.recipe.recipe.metadata.title == "custom 2m temperature"

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

    def test_former_python_product_available_with_required_parameters(self):
        definition = get_plot_definition("cn.shr.default")
        assert check_plot_available(definition, self._time_config(0), PlotConfig(
            "cn.shr.default", plot_params={"first_level": 1000})) is True


#: External v3 recipe using the same product runtime as packaged recipes.
EXTERNAL_RECIPE = """
api_version: cedarkit.plots/v3
kind: PlotRecipe
metadata: {name: custom.t2m, title: "custom 2m temperature"}
spec:
  data:
    temperature:
      field: {parameter: cedarkit.t2m}
      source_units: K
      units: degC
      temperature_kind: absolute
  content:
    charts:
      - id: main
        plots:
          - {id: temperature, method: contourf, field: temperature, style: "cemc.t2m:cn_summer", targets: all, data_crs: plate_carree}
        titles:
          - {id: heading, text: "2m Temperature (C)"}
    colorbars:
      - {id: temperature, plots: [{chart: main, plot: temperature}], label: "°C"}
  display: {template: east_asia}
"""
