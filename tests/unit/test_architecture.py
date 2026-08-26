"""AST guard for the task application's allowed runtime dependencies."""

import ast
from pathlib import Path

import cemc_plots_kit


PACKAGE_DIR = Path(cemc_plots_kit.__file__).parent


def test_task_package_has_no_reverse_imports():
    """The application is the top layer; this makes violations actionable."""
    offenders = []
    # There are no upper runtime packages today. Keep the explicit guard for
    # the param-db implementation package, which must stay package-data only.
    forbidden = ("cedarkit_param_db",)
    for path in PACKAGE_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if any(name == target or name.startswith(f"{target}.") for target in forbidden):
                    offenders.append(f"{path.relative_to(PACKAGE_DIR)}:{node.lineno} imports {name}")
    assert not offenders, "runtime packages must not import cedarkit_param_db:\n" + "\n".join(offenders)
