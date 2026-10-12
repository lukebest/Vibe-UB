"""Canonical contract YAML digest. Stand-in for ``scripts/gate/contract_hash.py``.

Gate definition of ``contract_sha256(path)`` (gate small PR, not on main):

1. Take the leading YAML block of the contract file.
2. ``yaml.safe_load`` it.
3. Use **all** fields (including ``assertions``).
4. ``json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)``.
5. Encode UTF-8, SHA-256 hex.

List order is preserved. Prose, indentation, and comments do not affect
the digest. When ``scripts/gate/contract_hash.py`` lands on this tree,
this module loads that file by path (no repo-root ``sys.path`` insert)
and uses its ``contract_sha256``. Until then this local copy is the
lockfile algorithm. Do not import an unmerged gate branch.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "contract_sha256 needs PyYAML (scripts/gate/requirements.txt)"
    ) from exc

_FRONT_MATTER_RE = re.compile(
    r"\A\s*---[ \t]*\n(.*?)\n---[ \t]*\s*(?:\n|\Z)",
    re.S,
)
_FENCE_RE = re.compile(
    r"\A\s*(?:#[^\n]*\n\s*)?```ya?ml[ \t]*\n(.*?)\n```",
    re.S,
)


def _extract_leading_yaml(text: str) -> str:
    match = _FRONT_MATTER_RE.search(text)
    if match:
        return match.group(1)
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1)
    raise ValueError("contract file has no leading YAML block")


def _canonical_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _local_contract_sha256(path: Path | str) -> str:
    dest = Path(path)
    raw = _extract_leading_yaml(dest.read_text(encoding="utf-8"))
    obj = yaml.safe_load(raw)
    return hashlib.sha256(_canonical_dumps(obj).encode("utf-8")).hexdigest()


def _gate_contract_hash_path() -> Path | None:
    here = Path(__file__).resolve()
    for base in here.parents:
        cand = base / "scripts" / "gate" / "contract_hash.py"
        if cand.is_file():
            return cand
    return None


def _load_gate_contract_sha256() -> Callable[[Path | str], str] | None:
    gate = _gate_contract_hash_path()
    if gate is None:
        return None
    spec = importlib.util.spec_from_file_location("_gate_contract_hash", gate)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, "contract_sha256", None)
    return fn if callable(fn) else None


_GATE_SHA256 = _load_gate_contract_sha256()


def contract_sha256(path: Path | str) -> str:
    """SHA-256 of the contract YAML object (canonical JSON). See module docstring."""
    if _GATE_SHA256 is not None:
        return _GATE_SHA256(path)
    return _local_contract_sha256(path)
