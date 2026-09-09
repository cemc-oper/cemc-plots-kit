from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("cemc_plots_kit")
except PackageNotFoundError:
    # package is not installed
    pass
