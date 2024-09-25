import pytest
from typer.testing import CliRunner


from cemc_esmi_plots.__main__ import app


@pytest.fixture
def runner():
    runner = CliRunner()
    return runner


def test_draw_height_500_mslp(runner, cma_gfs_system_name, cma_gfs_data_dir):
    result = runner.invoke(app, [
        "draw",
        "--system-name", cma_gfs_system_name,
        "--plot-type", "height_500_mslp",
        "--start-time", "2024092200",
        "--forecast-time", "24h",
        "--data-dir", cma_gfs_data_dir,
        "--work-dir", "/g7/JOB_TMP/wangdp/workspace/cedarkit/cemc_esmi_plots/tests/cma_hpc/cli/draw",
        "--data-file-name-template", "gmf.gra.{start_time_label}{forecast_hour_label}.grb2",
    ])

    assert result.exit_code == 0
