"""task YAML plots 段解析与 run_task 端到端测试。"""
import pandas as pd
import pytest

from cemc_plots_kit.task import bind_task_source, parse_plots_config, run_task
from test_plots import EXTERNAL_RECIPE


class TestParsePlotsConfig:
    def test_bool_switch(self):
        assert parse_plots_config({"cn.t2m": True, "cn.rain_24h": False}) == [("cn.t2m", {})]

    def test_string_switch(self):
        """字符串形式的 on/off（YAML 引号写法）。"""
        assert parse_plots_config({"cn.t2m": "on", "cn.rain_24h": "off"}) == [("cn.t2m", {})]

    def test_none_is_off(self):
        assert parse_plots_config({"cn.t2m": None}) == []

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


class TestRunTask:
    """端到端：MockDataSource 替换数据源，跑通 task 全流程（含外部配方）。"""

    def test_run_task(self, mock_data_source, start_time, tmp_path):
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()
        (recipe_dir / "t2m_custom.yaml").write_text(EXTERNAL_RECIPE, encoding="utf-8")

        task_file_path = tmp_path / "task.yaml"
        task_file_path.write_text(f"""
runtime:
  base_work_dir: {tmp_path / "run"}

source:
  data_dir: /not/used

system_name: CMA-GFS

time:
  start_time: {start_time.strftime("%Y%m%d%H")}
  forecast_time: 24h
  forecast_interval: 24h

plots:
  cn.t2m: on
  cn.rain_24h: on
  cn.rain_wind_10m:
    - {{ interval: 3h }}
    - {{ interval: 6h }}
  recipes/t2m_custom.yaml: on
""", encoding="utf-8")

        run_task(task_file_path=task_file_path)

        output_dir = tmp_path / "run" / "output"
        output_names = sorted(p.name for p in output_dir.glob("*.png"))

        start_time_label = start_time.strftime("%Y%m%d%H")
        expected = [
            # cn.t2m 无 time_diff，0h/24h 均可出图
            f"cn_t2m_{start_time_label}_000.png",
            f"cn_t2m_{start_time_label}_024.png",
            # cn.rain_24h 需要 24h 累计，0h 被 check_available 过滤
            f"cn_rain_24h_{start_time_label}_024.png",
            # 3h/6h 间隔在 0h 均被过滤，24h 出图；带参数后缀区分
            f"cn_rain_wind_10m_interval_3h_{start_time_label}_024.png",
            f"cn_rain_wind_10m_interval_6h_{start_time_label}_024.png",
            # 外部配方，输出名取文件 stem
            f"t2m_custom_{start_time_label}_000.png",
            f"t2m_custom_{start_time_label}_024.png",
        ]
        assert output_names == sorted(expected)


class TestTaskSourceBinding:
    def test_catalog_default_binds_canonical_source(self, tmp_path):
        config = bind_task_source("CMA-MESO", {}, tmp_path)
        assert config.dataset_id == "cma_meso_3km"
        assert config.source_spec.name == "local"
        assert config.source_spec.args == ("cma_meso_3km/grib2/orig",)

    def test_explicit_legacy_paths_bind_file_pattern_and_keep_system_label(self, tmp_path):
        config = bind_task_source(
            "CMA-GFS",
            {
                "data_dir": "fixture/{start_time_label}",
                "data_file_name_template": "gmf.{start_time_label}{forecast_hour_label}.grb2",
            },
            tmp_path,
        )
        assert config.system_name == "CMA-GFS"
        assert config.dataset_id == "cma_gfs_gmf"
        assert config.source_spec.name == "file-pattern"
        assert config.source_spec.args == (
            str(tmp_path / "fixture/{start_time_label}"),
            "gmf.{start_time_label}{forecast_hour_label}.grb2",
        )

    def test_partial_explicit_source_uses_only_matching_catalog_default(self, tmp_path):
        config = bind_task_source(
            "CMA-GFS", {"data_dir": "/fixture/{start_time_label}"}, tmp_path,
        )
        assert config.source_spec.name == "file-pattern"
        assert config.source_spec.args[1] == "gmf.gra.{start_time_label}{forecast_hour_label}.grb2"

    def test_unknown_partial_source_is_diagnostic(self, tmp_path):
        with pytest.raises(ValueError, match="unknown dataset"):
            bind_task_source("unknown", {"data_dir": "/fixture"}, tmp_path)
