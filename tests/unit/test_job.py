"""run_job 端到端与输出命名测试（cemc_plots_kit.job）。"""
from pathlib import Path

import os

import pandas as pd
import pytest
import matplotlib.pyplot as plt
from cedar_graph.testing import MockDataSource
from cedarkit.plots.workflow.render import WorkflowRenderError

from cemc_plots_kit.config import ExprConfig, JobConfig, PlotConfig, RuntimeConfig, TimeConfig
from cemc_plots_kit.job import (
    create_work_dir,
    get_output_image_file_name,
    run_job,
)


def _make_job_config(work_dir, plot_name, start_time, forecast_time, system_name, plot_params=None):
    return JobConfig(
        expr_config=ExprConfig(
            source_spec=None,
        ),
        runtime_config=RuntimeConfig(
            base_work_dir=str(work_dir),
        ),
        time_config=TimeConfig(
            start_time=start_time,
            forecast_time=forecast_time,
        ),
        plot_config=PlotConfig(
            plot_name=plot_name,
            plot_params=plot_params or {},
        ),
    )


class TestOutputNaming:
    def test_work_dir_uses_plot_label(self, tmp_path, start_time, forecast_time, system_name):
        job_config = _make_job_config(tmp_path, "cn.t2m", start_time, forecast_time, system_name)
        work_dir = create_work_dir(job_config)
        assert work_dir == Path(tmp_path, "202407010000", "cn_t2m", "024")

    def test_work_dir_params_suffix(self, tmp_path, start_time, forecast_time, system_name):
        job_config = _make_job_config(
            tmp_path, "cn.rain_wind_10m", start_time, forecast_time, system_name,
            plot_params={"interval": "3h"},
        )
        work_dir = create_work_dir(job_config)
        assert work_dir == Path(tmp_path, "202407010000", "cn_rain_wind_10m_interval_3h", "024")

    def test_image_file_name(self, tmp_path, start_time, forecast_time, system_name):
        job_config = _make_job_config(tmp_path, "cn.t2m", start_time, forecast_time, system_name)
        assert get_output_image_file_name(job_config) == "cn_t2m_2024070100_024.png"

    def test_image_file_name_recipe_path(self, tmp_path, start_time, forecast_time, system_name):
        job_config = _make_job_config(
            tmp_path, "recipes/t2m_custom.yaml", start_time, forecast_time, system_name,
        )
        assert get_output_image_file_name(job_config) == "t2m_custom_2024070100_024.png"


class TestRunJob:
    @pytest.mark.parametrize("error_type", [RuntimeError, KeyboardInterrupt])
    def test_failed_save_preserves_existing_output_and_caller_figure(
            self, monkeypatch, tmp_path, start_time, forecast_time, system_name, error_type):
        config = _make_job_config(tmp_path, "cn.t2m", start_time, forecast_time, system_name)
        output = tmp_path / "output" / get_output_image_file_name(config)
        output.parent.mkdir()
        output.write_bytes(b"previous complete image")
        figure = plt.figure()
        closed = []

        class FailingPanel:
            def save(self, path):
                Path(path).write_bytes(b"incomplete")
                raise error_type("save failed")

            def close(self):
                closed.append(True)

        monkeypatch.setattr("cemc_plots_kit.job.run_plot", lambda **kwargs: FailingPanel())
        with pytest.raises(error_type, match="save failed"):
            run_job(config, data_source=object())
        assert output.read_bytes() == b"previous complete image"
        assert list(output.parent.glob(".*.tmp.png")) == []
        assert closed == [True]
        assert plt.fignum_exists(figure.number)
        plt.close(figure)

    @pytest.mark.parametrize("error_type", [KeyboardInterrupt, RuntimeError])
    def test_failed_render_closes_its_panel_and_preserves_caller_figure(
            self, monkeypatch, mock_data_source, tmp_path, start_time, forecast_time, system_name, error_type):
        config = _make_job_config(tmp_path, "cn.t2m", start_time, forecast_time, system_name)
        caller = plt.figure()
        owned = plt.figure()

        class InterruptedPanel:
            def render(self):
                raise error_type("render interrupted")

            def close(self):
                plt.close(owned)

        monkeypatch.setattr("cemc_plots_kit.job.render_result", lambda *args, **kwargs: InterruptedPanel())
        expected_error = KeyboardInterrupt if error_type is KeyboardInterrupt else WorkflowRenderError
        with pytest.raises(expected_error, match="render interrupted") as caught:
            run_job(config)
        if error_type is RuntimeError:
            assert caught.value.path == "render"
            assert isinstance(caught.value.cause, RuntimeError)
        assert not plt.fignum_exists(owned.number)
        assert plt.fignum_exists(caller.number)
        assert list((tmp_path / "output").glob("*.png")) == []
        plt.close(caller)

    def test_run_job_restores_working_directory(
            self, mock_data_source, tmp_path, start_time, forecast_time, system_name
    ):
        """Stage-0 normal-path contract; exceptional cleanup is tracked as M-11."""
        job_config = _make_job_config(
            tmp_path, "cn.t2m", start_time, forecast_time, system_name,
        )
        before = os.getcwd()
        run_job(job_config=job_config)
        assert os.getcwd() == before

    def test_run_job_restores_working_directory_after_error(
            self, monkeypatch, tmp_path, start_time, forecast_time, system_name
    ):
        job_config = _make_job_config(
            tmp_path, "cn.t2m", start_time, forecast_time, system_name,
        )
        monkeypatch.setattr(
            "cemc_plots_kit.job.run_plot",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("plot failed")),
        )
        before = os.getcwd()
        with pytest.raises(RuntimeError, match="plot failed"):
            run_job(job_config=job_config, data_source=object())
        assert os.getcwd() == before

    def test_run_job_never_changes_working_directory(
            self, mock_data_source, monkeypatch, tmp_path, start_time, forecast_time, system_name
    ):
        job_config = _make_job_config(tmp_path, "cn.t2m", start_time, forecast_time, system_name)
        monkeypatch.setattr("cemc_plots_kit.job.os.chdir", lambda path: pytest.fail("run_job changed cwd"))
        run_job(job_config)

    """端到端：MockDataSource 替换数据源，run_job 出图。"""

    def test_run_job_recipe(self, mock_data_source, tmp_path, start_time, forecast_time, system_name):
        job_config = _make_job_config(tmp_path, "cn.t2m", start_time, forecast_time, system_name)

        output_file_list = run_job(job_config)

        assert len(output_file_list) == 1
        output_file = output_file_list[0]
        assert output_file == Path(tmp_path, "output", "cn_t2m_2024070100_024.png")
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        assert len(mock_data_source.workflow_requests) == 1
        assert mock_data_source.workflow_requests[0].key.parameter_id == "cedarkit.t2m"

    def test_run_job_recipe_with_params(self, mock_data_source, tmp_path, start_time, forecast_time, system_name):
        job_config = _make_job_config(
            tmp_path, "cn.rain_wind_10m", start_time, forecast_time, system_name,
            plot_params={"interval": "3h"},
        )

        output_file_list = run_job(job_config)

        output_file = output_file_list[0]
        assert output_file == Path(tmp_path, "output", "cn_rain_wind_10m_interval_3h_2024070100_024.png")
        assert output_file.exists()

    def test_run_job_python_module(self, mock_data_source, tmp_path, start_time, forecast_time, system_name):
        """The former Python shear product uses the v3 job path and its level parameter."""
        job_config = _make_job_config(
            tmp_path, "cn.shr.default", start_time, forecast_time, system_name,
            plot_params={"first_level": 1000},
        )

        output_file_list = run_job(job_config)

        output_file = output_file_list[0]
        assert output_file == Path(tmp_path, "output", "cn_shr_default_first_level_1000_2024070100_024.png")
        assert output_file.exists()
        assert len(mock_data_source.workflow_requests) == 1

    @pytest.mark.parametrize("name,params,reads", (
        ("div_wind", {"div_level": 850, "wind_level": 850}, 3),
        ("pte_wind", {"wind_level": 850, "pte_first_level": 500, "pte_second_level": 850}, 4),
        ("qv_div", {"level": 850}, 1),
        ("shr", {"first_level": 3000}, 1),
        ("t_dew_t", {"level": 850}, 2),
    ))
    def test_former_python_products_save_v3_output(
            self, tmp_path, start_time, forecast_time, system_name, name, params, reads):
        source = MockDataSource(resolution=2)
        config = _make_job_config(tmp_path, f"cn.{name}.default", start_time, forecast_time,
                                  system_name, plot_params=params)
        outputs = run_job(config, data_source=source)
        assert len(outputs) == 1
        assert outputs[0].exists() and outputs[0].stat().st_size > 0
        assert len(source.workflow_requests) == reads

    def test_ensemble_job_creates_member_control_and_max_output(
            self, tmp_path, start_time, forecast_time, system_name):
        source = MockDataSource(resolution=5)
        config = _make_job_config(tmp_path, "cn.ens_t2m", start_time, forecast_time,
                                  system_name, plot_params={"member_ids": ["m01", "m02"],
                                                            "control_id": "ctl"})
        outputs = run_job(config, data_source=source)
        assert len(outputs) == 1
        assert outputs[0].exists() and outputs[0].stat().st_size > 0
        assert "member_ids_m01-m02" in outputs[0].name
        assert {(request.key.query.to_dict().get("member"), request.key.query.to_dict().get("member_role"))
                for request in source.workflow_requests} == {(None, "control"), (1, "perturbation"), (2, "perturbation")}

    def test_run_job_external_recipe(self, mock_data_source, tmp_path, start_time, forecast_time, system_name):
        recipe_path = tmp_path / "t2m_custom.yaml"
        recipe_path.write_text(EXTERNAL_RECIPE, encoding="utf-8")
        job_config = _make_job_config(tmp_path, str(recipe_path), start_time, forecast_time, system_name)

        output_file_list = run_job(job_config)

        output_file = output_file_list[0]
        assert output_file == Path(tmp_path, "output", "t2m_custom_2024070100_024.png")
        assert output_file.exists()


from test_plots import EXTERNAL_RECIPE


def test_member_absence_is_a_missing_field_and_ensemble_summary_survives_worker_result():
    from cedar_graph.recipes.ensemble_product import MissingMemberError
    from cemc_plots_kit.errors import classify_error, is_missing_error
    from cemc_plots_kit.execution import _result_from_worker
    assert is_missing_error(MissingMemberError('m002'))
    assert classify_error(MissingMemberError('m002')) == 'field_missing'
    summary = {'max_input_ids': ['m001'], 'max_realized_input_count': 1}
    result, failed = _result_from_worker({'status': 'success', 'job_id': 'ensemble',
        'outputs': [], 'ensemble': summary}, 'fail')
    assert not failed and result['ensemble'] == summary
