from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("cemc_esmi_plots")
except PackageNotFoundError:
    # package is not installed
    pass
