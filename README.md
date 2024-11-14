# cemc-plots-kit

A plotting tool for Numerical Weather Prediction model data of CEMC.

## Install

Download the latest source code from GitHub and install manually.

## Getting started

### Single plot

Draw a single figure in command line.

The following command draws a figure for 2m temperature using CMA-GFS data in CMA-HPC.

```shell
python -m cemc_plots_kit draw \
  --system-name cma_gfs \
  --plot-type t_2m \
  --start-time 2024111300 \
  --forecast-time 24h \
  --work-dir .
```

The command will generate an image file named `t_2m_2024111300_024.png` in current directory.

### Batch plot

Draw a batch of figures using a task file.

Create a task file named `task.yaml` with content:

```yaml
runtime:
  base_work_dir: .

source:
  data_dir: /g3/COMMONDATA/OPER/CEMC/GFS_GMF/Prod-grib/{start_time_label}/ORIG

system_name: CMA-GFS

time:
  start_time: 2024111300
  forecast_time: 48h
  forecast_interval: 6h

plots:
  height_500_mslp: on
  rain_24h: on
```

Execute the following shell command to draw figures:

```shell
python -m cemc_plots_kit task --task-file ./task.yaml
```

When the command is executed, there are 14 image files in output directory:

```text
height_500_mslp_2024111300_000.png
height_500_mslp_2024111300_006.png
height_500_mslp_2024111300_012.png
height_500_mslp_2024111300_018.png
height_500_mslp_2024111300_024.png
height_500_mslp_2024111300_030.png
height_500_mslp_2024111300_036.png
height_500_mslp_2024111300_042.png
height_500_mslp_2024111300_048.png
rain_24h_2024111300_024.png
rain_24h_2024111300_030.png
rain_24h_2024111300_036.png
rain_24h_2024111300_042.png
rain_24h_2024111300_048.png
```

## LICENSE

Copyright &copy; 2024, developers at cemc-oper.

`cemc-plots-kit` is licensed under [Apache License V2.0](./LICENSE)
