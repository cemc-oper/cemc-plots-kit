import importlib


def get_plot_module(plot_name: str, module_name: str = "cemc_plots_kit.plots"):
    plot_module = importlib.import_module(f"{module_name}.{plot_name}")
    return plot_module
