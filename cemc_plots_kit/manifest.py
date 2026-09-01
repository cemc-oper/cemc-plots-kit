"""Atomic, credential-free task manifest publication."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def write_manifest(path: Path, document: dict[str, Any]) -> Path:
    """Write a JSON manifest by same-directory atomic replacement."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(document, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return path
