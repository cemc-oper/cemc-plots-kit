from cemc_plots_kit.config import (
    get_default_data_dir,
    get_default_data_file_name_template,
)


def test_catalog_backed_defaults_follow_meso_decision():
    assert "MESO_3KM" in get_default_data_dir("CMA-MESO")
    assert "MESO_1KM" in get_default_data_dir("CMA-MESO-1KM")
    assert get_default_data_file_name_template("CMA-GFS") == (
        "gmf.gra.{start_time_label}{forecast_hour_label}.grb2"
    )


def test_unknown_default_remains_compatible():
    assert get_default_data_dir("not-a-system") is None
    assert get_default_data_file_name_template("not-a-system") is None
