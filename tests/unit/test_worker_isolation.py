"""Real spawned workers exercising the migrated product and output paths."""

from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
from importlib.resources import files
from multiprocessing import get_context
from pathlib import Path
import gc
import os
import weakref

import cartopy.crs  # Import native map libraries before the data backend in spawned workers.
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
import reki
import xarray as xr
import yaml

from cedar_graph.data import RekiProvider
from cedar_graph.recipes.ensemble_product import EnsembleRequest, EnsembleT2MProduct
from cedar_graph.recipes.workflow_product import WorkflowProduct, select_workflow_product
from cedar_graph.testing import MockDataSource
from cedarkit.plots.plan.provider import BoundFieldRequest
from cedarkit.plots.style.registry import get_default_registry
from cedarkit.plots.types import AreaRange

from cemc_plots_kit.config import ExprConfig, JobConfig, PlotConfig, RuntimeConfig, TimeConfig
import cemc_plots_kit.job as job_module
from cemc_plots_kit.job import run_job
from cemc_plots_kit.plots import get_plot_definition, workflow_context


AREAS = {
    "east": {"start_longitude": 75.0, "end_longitude": 140.0,
             "start_latitude": 15.0, "end_latitude": 55.0},
    "china": {"start_longitude": 95.0, "end_longitude": 125.0,
              "start_latitude": 20.0, "end_latitude": 45.0},
}


def _trace_probe(area, label):
    """Use a real provider cache and trace without external files."""
    field = xr.DataArray([[273.15]], dims=("latitude", "longitude"),
                         coords={"latitude": [30.0], "longitude": [110.0]}, attrs={"units": "K"})

    class Reader:
        def sel(self, query):
            return self

        def one(self):
            return self

        def to_xarray(self):
            return field

    original = reki.from_source
    reki.from_source = lambda *args, **kwargs: Reader()
    provider = RekiProvider(reki.SourceSpec("local", args=("synthetic",)), region=area)
    try:
        plan = select_workflow_product("cn.t2m").compile(
            workflow_context(TimeConfig(pd.Timestamp("2024-07-01"), pd.Timedelta("24h")),
                             PlotConfig("cn.t2m")))
        key = next(node.request for node in plan.nodes if node.request is not None)
        requests = (BoundFieldRequest(f"{label}:first", key, "isolation"),
                    BoundFieldRequest(f"{label}:second", key, "isolation"))
        provider.fetch_many(requests)
        evidence = {"region": provider.region, "cache": dict(provider.cache_info),
                    "trace": [(item.node_id, item.status) for item in provider.trace]}
    finally:
        provider.close()
        reki.from_source = original
    evidence["closed_entries"] = provider.cache_info["entries"]
    evidence["closed_trace"] = len(provider.trace)
    return evidence


def _run_case(case, output_root, barrier=None):
    if barrier is not None:
        barrier.wait(timeout=60)
    output_root = Path(output_root)
    area = AREAS[case["area"]]
    start_time = pd.Timestamp("2024-07-01")
    forecast_time = pd.Timedelta("24h")
    config = JobConfig(
        expr_config=ExprConfig(system_name="CMA-GFS", data_dir="", area=AreaRange(**area)),
        runtime_config=RuntimeConfig(work_dir=output_root / "work", output_dir=output_root / "output"),
        time_config=TimeConfig(start_time, forecast_time),
        plot_config=PlotConfig(case["plot"], plot_params=case["params"]),
    )
    before_figures = tuple(plt.get_fignums())
    registry = get_default_registry()
    registry_before = repr(registry._lookup("cemc.t2m:cn_summer")[3].model_dump())
    source = MockDataSource(resolution=5)
    owned = []
    original_run_plot = job_module.run_plot

    def capture_plot(*args, **kwargs):
        panel = original_run_plot(*args, **kwargs)
        owned.append(weakref.ref(panel))
        first_chart = next(iter(panel.charts.values()))
        first_layer = next(iter(first_chart.layers.values()))
        artist = next(iter(next(iter(first_layer.results.values())).artists))
        owned.append(weakref.ref(artist))
        return panel

    job_module.run_plot = capture_plot
    try:
        outputs = run_job(config, data_source=source)
    except Exception as exc:
        if not case.get("fail"):
            raise
        assert tuple(plt.get_fignums()) == before_figures
        assert not list((output_root / "output").glob("*.png"))
        return {"pid": os.getpid(), "status": "failed", "error": type(exc).__name__,
                "requests": len(source.workflow_requests), "figures": before_figures}
    finally:
        job_module.run_plot = original_run_plot
    assert not case.get("fail")
    gc.collect()
    assert all(reference() is None for reference in owned)
    output = outputs[0]
    assert output.exists() and output.parent == output_root / "output"
    assert tuple(plt.get_fignums()) == before_figures
    assert registry_before == repr(registry._lookup("cemc.t2m:cn_summer")[3].model_dump())
    assert not list(output.parent.glob(".*.tmp.png"))

    definition = get_plot_definition(case["plot"])
    data_source = MockDataSource(resolution=5)
    if isinstance(definition, EnsembleT2MProduct):
        prepared = definition.prepare(data_source, start_time=start_time, forecast_time=forecast_time,
                                      request=EnsembleRequest.from_params(case["params"]))
        values = {name: float(field.sum()) for name, field in prepared.fields.items()}
        values["max"] = float(prepared.max_field.sum())
        content = tuple(([prepared.realized_control_id] if prepared.realized_control_id else []) +
                        list(prepared.realized_member_ids) + (["max"] if prepared.max_field is not None else []))
        styles = (prepared.style_variant,)
    else:
        assert isinstance(definition, WorkflowProduct)
        plan = definition.compile(workflow_context(config.time_config, config.plot_config))
        result = plan.execute(data_source, registry=definition.discovery.ops)
        values = {name: float(field.sum()) for name, field in result.outputs.items()}
        content = tuple(chart.id for chart in result.content.charts)
        styles = tuple(plot.style for chart in result.content.charts for plot in chart.plots)
    with Image.open(output) as image:
        pixels = sha256(np.asarray(image.convert("RGBA")).tobytes()).hexdigest()
    return {"pid": os.getpid(), "status": "success", "output": output.name,
            "pixels": pixels, "values": values, "content": content, "styles": styles,
            "requests": len(source.workflow_requests), "members": tuple(
                request.key.query.member for request in source.workflow_requests),
            "figures": before_figures, "trace": _trace_probe(area, case["name"])}


def test_reused_worker_and_parallel_workers_keep_task_state_isolated(tmp_path):
    recipe = yaml.safe_load(files("cedar_graph.recipes").joinpath("workflow/cn/t2m.yaml").read_text())
    recipe["metadata"]["name"] = "custom.cn_area_t2m"
    recipe["spec"]["display"]["template"] = "cn_area"
    recipe["spec"]["params"]["style_variant"]["default"] = "cn_winter"
    external = tmp_path / "cn-area.yaml"
    external.write_text(yaml.safe_dump(recipe), encoding="utf-8")

    summer = {"name": "summer", "plot": "cn.t2m", "params": {"style_variant": "cn_summer"}, "area": "east"}
    winter = {"name": "winter", "plot": str(external), "params": {}, "area": "china"}
    ensemble = {"name": "members", "plot": "cn.ens_t2m",
                "params": {"member_ids": ["m01", "m02"], "control_id": "ctl", "columns": 3}, "area": "china"}
    failure = {"name": "failure", "plot": "cn.t2m", "params": {"style_variant": "invalid"},
               "area": "east", "fail": True}

    context = get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        sequential = [pool.submit(_run_case, case, tmp_path / "serial" / case["name"]).result()
                      for case in (summer, failure, winter, ensemble,
                                   {**summer, "name": "summer-again"})]
    assert len({item["pid"] for item in sequential}) == 1
    assert [item["status"] for item in sequential] == ["success", "failed", "success", "success", "success"]
    assert sequential[0]["pixels"] == sequential[-1]["pixels"]
    assert sequential[0]["values"] == sequential[-1]["values"]
    assert sequential[0]["styles"] == sequential[-1]["styles"]
    assert sequential[0]["output"] == sequential[-1]["output"]
    assert sequential[0]["pixels"] != sequential[2]["pixels"]
    assert sequential[0]["styles"] != sequential[2]["styles"]
    assert sequential[3]["content"] == ("ctl", "m01", "m02", "max")
    assert set(sequential[3]["members"]) == {"ctl", "m01", "m02"}
    assert all(item["requests"] == 1 for item in (sequential[0], sequential[2], sequential[-1]))
    for item in (sequential[0], sequential[2], sequential[3], sequential[-1]):
        trace = item["trace"]
        assert trace["region"] == AREAS["east" if item is sequential[0] or item is sequential[-1] else "china"]
        assert trace["cache"] == {"hits": 1, "misses": 1, "entries": 1}
        assert [status for _, status in trace["trace"]] == ["ok", "cached"]
        assert trace["closed_entries"] == trace["closed_trace"] == 0

    with context.Manager() as manager:
        barrier = manager.Barrier(3)
        with ProcessPoolExecutor(max_workers=3, mp_context=context) as pool:
            futures = [pool.submit(_run_case, case, tmp_path / "parallel" / case["name"], barrier)
                       for case in (summer, winter, ensemble)]
            parallel = [future.result() for future in futures]
    assert len({item["pid"] for item in parallel}) == 3
    for single, many in zip((sequential[0], sequential[2], sequential[3]), parallel):
        assert single["values"] == many["values"]
        assert single["content"] == many["content"]
        assert single["styles"] == many["styles"]
        assert single["pixels"] == many["pixels"]
        assert single["output"] == many["output"]
