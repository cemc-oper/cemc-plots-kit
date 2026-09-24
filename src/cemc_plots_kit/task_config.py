"""Helpers for the versioned task model."""

from __future__ import annotations

from typing import Any


def parse_plots_config(plots_config: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Expand enabled plot IDs and their parameter sets in document order."""

    selected: list[tuple[str, dict[str, Any]]] = []
    for plot_name, value in plots_config.items():
        if value is False:
            continue
        if value is True:
            selected.append((plot_name, {}))
        elif isinstance(value, dict):
            selected.append((plot_name, dict(value)))
        elif isinstance(value, list):
            for item in value:
                selected.append((plot_name, dict(item) if item else {}))
        else:
            raise ValueError(
                f"invalid plots entry for {plot_name!r}: {value!r}; "
                "expected a boolean, parameter mapping or list of parameter mappings"
            )
    return selected
