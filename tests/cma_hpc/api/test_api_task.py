import shutil
from pathlib import Path

import pytest

from cemc_esmi_plots.task import run_task


@pytest.fixture
def base_work_dir(root_work_dir):
    return f"{root_work_dir}/api/task"


def test_run_task_cn(cma_gfs_system_name, last_two_day, cma_gfs_data_dir, base_work_dir):
    system_name = cma_gfs_system_name
    start_time = last_two_day
    start_time_label = start_time.strftime("%Y%m%d%H")
    data_dir = cma_gfs_data_dir
    case_base_work_dir = f"{base_work_dir}/cn/{system_name}"
    task_file_path = Path(case_base_work_dir) / "task.yaml"

    shutil.rmtree(case_base_work_dir, ignore_errors=True)
    Path(case_base_work_dir).mkdir(parents=True, exist_ok=True)

    task_file_content = f"""
runtime:
  base_work_dir: {case_base_work_dir}

source:
  data_dir: {data_dir}

system_name: {system_name}

time:
  start_time: {start_time_label}
  forecast_time: 48h
  forecast_interval: 6h

plots:
  height_500_mslp: on
  rain_1h_wind_10m: off
  rain_24h: on
"""
    with open(task_file_path, "w") as f:
        f.write(task_file_content)

    run_task(task_file_path=task_file_path)


def test_run_task_area(cma_gfs_system_name, last_two_day, cma_gfs_data_dir, base_work_dir, cn_area_north_china):
    system_name = cma_gfs_system_name
    start_time = last_two_day
    start_time_label = start_time.strftime("%Y%m%d%H")
    data_dir = cma_gfs_data_dir
    area = cn_area_north_china.area
    case_base_work_dir = f"{base_work_dir}/north_china/{system_name}"
    task_file_path = Path(case_base_work_dir) / "task.yaml"

    shutil.rmtree(case_base_work_dir, ignore_errors=True)
    Path(case_base_work_dir).mkdir(parents=True, exist_ok=True)

    task_file_content = f"""
runtime:
  base_work_dir: {case_base_work_dir}

source:
  data_dir: {data_dir}

system_name: {system_name}

area:
  start_latitude: {area.start_latitude}
  end_latitude: {area.end_latitude}
  start_longitude: {area.start_longitude}
  end_longitude: {area.end_longitude}

time:
  start_time: {start_time_label}
  forecast_time: 48h
  forecast_interval: 6h

plots:
  height_500_mslp: on
  rain_1h_wind_10m: off
  rain_24h: on
"""
    with open(task_file_path, "w") as f:
        f.write(task_file_content)

    run_task(task_file_path=task_file_path)
