import pytest
from typer.testing import CliRunner


from cemc_esmi_plots.__main__ import app


@pytest.fixture
def runner():
    runner = CliRunner()
    return runner


def test_draw_height_500_mslp(runner):
    result = runner.invoke(app, [
        "draw",
        "--system-name", "cma_meso",
        "--plot-type", "height_500_mslp",
        "--start-time", "2024092200",
        "--forecast-time", "24h",
        "--data-dir", "/g3/COMMONDATA/OPER/CEMC/GFS_GMF/Prod-grib/2024092200/ORIG",
        "--work-dir", "/g7/JOB_TMP/wangdp/workspace/cedarkit/cemc_esmi_plots/tests/cma_hpc",
    ])

    assert result.exit_code == 0
