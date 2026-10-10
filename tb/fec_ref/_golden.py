"""Load tb/models/ub_pcs_fec.py by file path.

SPEC §2.2: PYTHONPATH starts at <repo>/pycircuit; the repo root stays off
sys.path. Do not `import tb.models`.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_TB_DIR = Path(__file__).resolve().parents[1]
_MODEL_PATH = _TB_DIR / "models" / "ub_pcs_fec.py"
_VECTOR_PATH = _TB_DIR / "models" / "ub_pcs_fec_vectors.json"
_REPO_ROOT = _TB_DIR.parent


def assert_import_root() -> None:
    """Repo root must not be on PYTHONPATH (SPEC §2.2). cocotb may still
    put the test directory on sys.path; that is not the repo root."""
    import os

    root = _REPO_ROOT.resolve()
    pyc = (root / "pycircuit").resolve()
    raw = os.environ.get("PYTHONPATH", "")
    parts = [p for p in raw.split(os.pathsep) if p and p != "."]
    if not parts:
        raise RuntimeError("PYTHONPATH is empty; expected <repo>/pycircuit first")
    first = Path(parts[0]).resolve()
    if first != pyc:
        raise RuntimeError(f"PYTHONPATH[0]={first} is not {pyc}")
    for item in parts:
        try:
            if Path(item).resolve() == root:
                raise RuntimeError(
                    f"repo root {root} is on PYTHONPATH; put <repo>/pycircuit first"
                )
        except OSError:
            continue


def load_golden():
    assert_import_root()
    spec = importlib.util.spec_from_file_location("ub_pcs_fec_golden", _MODEL_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load golden from {_MODEL_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_vectors() -> dict:
    return json.loads(_VECTOR_PATH.read_text(encoding="utf-8"))


def pack_symbols(symbols) -> int:
    acc = 0
    for s in symbols:
        acc = (acc << 8) | (int(s) & 0xFF)
    return acc


def unpack_symbols(word: int, n: int) -> list[int]:
    out = [0] * n
    for i in range(n - 1, -1, -1):
        out[i] = word & 0xFF
        word >>= 8
    return out
