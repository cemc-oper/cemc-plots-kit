import importlib


def get_plot_module(plot_name: str):
    plot_module = importlib.import_module(f"cemc_esmi_plots.plots.{plot_name}")
    return plot_module
