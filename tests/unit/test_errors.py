import reki

from cemc_plots_kit.errors import classify_error


def _error(name):
    return type(name, (RuntimeError,), {})()


def test_classify_error_keeps_missing_ambiguity_and_runtime_categories_distinct(tmp_path):
    assert classify_error(reki.DataNotFoundError(reki.FieldQuery(parameter="t2m"))) == "field_missing"
    assert classify_error(reki.MultipleFieldsMatchedError(reki.FieldQuery(parameter="t2m"), "source", 2)) == "multiple_fields"
    assert classify_error(FileNotFoundError(), storage_base=str(tmp_path / "missing-mount")) == "mount_missing"
    assert classify_error(FileNotFoundError(), storage_base=str(tmp_path)) == "file_missing"
    assert classify_error(_error("IndexBuildError")) == "index_error"
    assert classify_error(_error("DecodeError")) == "decode_error"
    assert classify_error(_error("RenderError")) == "render_error"
    assert classify_error(_error("PublishError")) == "publish_error"
