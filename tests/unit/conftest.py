"""
本地单元测试：不依赖 CMA-HPC 数据。

端到端用例通过 monkeypatch ``cemc_plots_kit.job.create_data_source``
替换为 ``cedar_graph.testing.MockDataSource``（确定性合成场），
覆盖 plot_type 解析 → 数据加载 → 出图的完整链路。
"""
import sys

import pandas as pd
import matplotlib
import cartopy.crs  # Load PROJ before the synthetic provider imports ecCodes.
import pytest
from loguru import logger

from cedar_graph.testing import MockDataSource

# Use non-interactive backend
matplotlib.use("Agg")


@pytest.fixture
def start_time() -> pd.Timestamp:
    return pd.Timestamp("2024-07-01 00:00:00")


@pytest.fixture
def forecast_time() -> pd.Timedelta:
    return pd.Timedelta(hours=24)


@pytest.fixture
def system_name() -> str:
    return "CMA-GFS"


@pytest.fixture
def mock_data_source(monkeypatch) -> MockDataSource:
    """将 job 的数据源替换为 MockDataSource（合成场，无需真实数据文件）。"""
    source = MockDataSource()
    monkeypatch.setattr(
        "cemc_plots_kit.job.create_data_source",
        lambda expr_config: source,
    )
    return source


logger.remove()
logger.add(sys.stderr, level="WARNING")
