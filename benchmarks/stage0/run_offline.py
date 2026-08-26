"""Offline-required Stage-0 plotting benchmarks.

Run from ``app/cemc-plots-kit``::

    uv run --no-sync python benchmarks/stage0/run_offline.py B0-2 result.json
    uv run --no-sync python benchmarks/stage0/run_offline.py B0-3 result.json
"""
import json
import resource
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")

from cedar_graph.testing import MockDataSource
from cemc_plots_kit.config import ExprConfig, JobConfig, PlotConfig, RuntimeConfig, TimeConfig
import cemc_plots_kit.job as job


# Deliberately fixed workload; parameter variants are distinct product requests.
B0_2_PRODUCTS = [
    ("cn.t2m", {}), ("cn.t2m", {"variant": "default"}),
    ("cn.rain_wind_10m", {"interval": "3h"}), ("cn.rain_wind_10m", {"interval": "6h"}),
    ("cn.shr.default", {"first_level": 1000}), ("cn.shr.default", {"first_level": 925}),
    ("cn.t2m", {"variant": "default", "label": "a"}), ("cn.t2m", {"variant": "default", "label": "b"}),
    ("cn.t2m", {"variant": "default", "label": "c"}), ("cn.t2m", {"variant": "default", "label": "d"}),
]
B0_3_PRODUCTS = [("cn.t2m", {}), ("cn.shr.default", {"first_level": 1000})]


def config(base, name, params, forecast):
    return JobConfig(
        ExprConfig("CMA-GFS", "/offline/mock", data_file_name_template="unused"),
        TimeConfig(pd.Timestamp("2024-07-01 00:00:00"), forecast),
        RuntimeConfig(base_work_dir=base), PlotConfig(name, params),
    )


def run_jobs(products, forecasts):
    with tempfile.TemporaryDirectory(prefix="cedarkit-stage0-") as temp:
        source = MockDataSource(resolution=2.0)
        original = job.create_data_source
        job.create_data_source = lambda expr: source
        try:
            load_seconds = render_seconds = 0.0
            paths = []
            for forecast in forecasts:
                for name, params in products:
                    jc = config(temp, name, params, forecast)
                    definition = job.get_plot_definition(name, base_dir=None)
                    started = time.perf_counter()
                    # run_plot combines operations, but its log boundary is not an API;
                    # load_data is timed directly before the rendering call.
                    metadata_kwargs = dict(start_time=jc.time_config.start_time, forecast_time=forecast,
                                           system_name="CMA-GFS", **params)
                    import inspect
                    metadata = definition.PlotMetadata(**{k: v for k, v in metadata_kwargs.items()
                        if k in inspect.signature(definition.PlotMetadata).parameters})
                    loader = __import__("cedar_graph.data", fromlist=["DataLoader"]).DataLoader(source)
                    data = definition.load_data(data_loader=loader, **{k: v for k, v in metadata_kwargs.items()
                        if k in inspect.signature(definition.load_data).parameters})
                    load_seconds += time.perf_counter() - started
                    started = time.perf_counter()
                    panel = definition.plot(plot_data=data, plot_metadata=metadata)
                    path = Path(temp) / f"{len(paths):03d}.png"
                    panel.save(path)
                    paths.append(path)
                    render_seconds += time.perf_counter() - started
            return {"data_loading_seconds": load_seconds, "rendering_seconds": render_seconds,
                    "figure_count": len(paths), "output_bytes": sum(p.stat().st_size for p in paths)}
        finally:
            job.create_data_source = original


def measure(scenario):
    products = B0_2_PRODUCTS if scenario == "B0-2" else B0_3_PRODUCTS
    forecasts = [pd.Timedelta(hours=24)] if scenario == "B0-2" else list(pd.timedelta_range("0h", "72h", freq="6h"))
    tracemalloc.start(); started = time.perf_counter()
    values = run_jobs(products, forecasts)
    _, values["python_peak_bytes"] = tracemalloc.get_traced_memory(); tracemalloc.stop()
    values["wall_time_seconds"] = time.perf_counter() - started
    values["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    values.update(file_open_count=None, grib_header_scan_count=0, value_decode_count=0)
    return values


def main(scenario, output):
    measure(scenario)  # warm-up
    runs = [measure(scenario) for _ in range(5)]
    times = [r["wall_time_seconds"] for r in runs]
    Path(output).write_text(json.dumps({"scenario": scenario, "profile": "offline-required", "source": "MockDataSource(resolution=2.0)",
        "products": B0_2_PRODUCTS if scenario == "B0-2" else B0_3_PRODUCTS, "runs": runs,
        "summary": {"wall_time_seconds": {"min": min(times), "median": statistics.median(times), "max": max(times)}},
        "note": "Mock profile measures deterministic provider and rendering work, not GRIB I/O."}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
