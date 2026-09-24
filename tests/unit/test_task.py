"""Versioned task plot selection parsing."""
import pytest

from cemc_plots_kit.task_config import parse_plots_config


class TestParsePlotsConfig:
    def test_bool_switch(self):
        assert parse_plots_config({"cn.t2m": True, "cn.rain_24h": False}) == [("cn.t2m", {})]

    def test_params_mapping(self):
        assert parse_plots_config({"cn.rain_wind_10m": {"interval": "3h"}}) == [
            ("cn.rain_wind_10m", {"interval": "3h"}),
        ]

    def test_params_list(self):
        """同一图形的多组参数（如多个降水时段）。"""
        assert parse_plots_config({"cn.rain_wind_10m": [{"interval": "1h"}, {"interval": "3h"}]}) == [
            ("cn.rain_wind_10m", {"interval": "1h"}),
            ("cn.rain_wind_10m", {"interval": "3h"}),
        ]

    def test_recipe_path_key(self):
        assert parse_plots_config({"recipes/t2m_custom.yaml": True}) == [
            ("recipes/t2m_custom.yaml", {}),
        ]

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError, match="cn.t2m"):
            parse_plots_config({"cn.t2m": 42})
