import reki
from cedarkit.plots.workflow.runtime import PlanExecutionError

from cemc_plots_kit.errors import classify_error, is_missing_error


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


def test_public_error_codes_do_not_hide_decode_or_service_failures():
    assert is_missing_error(reki.QueryError("no_match"))
    assert classify_error(reki.QueryError("no_match")) == "field_missing"
    for error in (reki.SourceError("decode_failed"), reki.SourceError("service_error"),
                  reki.QueryError("multiple_matches"), reki.SourceError("resource_not_found")):
        code = error.code
        assert not is_missing_error(error)
        assert classify_error(error) == code
        wrapped = PlanExecutionError("temperature", "cn.t2m", "recipe.yaml:12", str(error), cause=error)
        assert not is_missing_error(wrapped)
        assert classify_error(wrapped) == code
    wrapped_missing = PlanExecutionError("temperature", "cn.t2m", "recipe.yaml:12", "missing",
                                         cause=reki.QueryError("no_match"))
    assert is_missing_error(wrapped_missing)
    assert classify_error(wrapped_missing) == "field_missing"
