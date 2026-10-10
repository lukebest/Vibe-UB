"""Single import site for leaf goldens.

Prefer top-level ``model/`` (architecture migration). Fall back to
``tb/models``. After that move lands, only this file changes.
Do not import goldens from test files any other way.
"""

from __future__ import annotations

import importlib
from types import ModuleType

_CANDIDATES = ("model", "tb.models")


def load_golden(mod_name: str) -> ModuleType:
    errors: list[str] = []
    for pkg in _CANDIDATES:
        qual = f"{pkg}.{mod_name}"
        try:
            return importlib.import_module(qual)
        except ModuleNotFoundError as exc:
            errors.append(f"{qual}: {exc}")
    raise ImportError(
        f"golden {mod_name!r} not found in {_CANDIDATES}: " + "; ".join(errors)
    )


lane_dist = load_golden("ub_pcs_lane_dist")
bcrc = load_golden("ub_dll_bcrc")
