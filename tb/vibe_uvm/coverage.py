"""Functional coverage scaffold (CoverPoint / CoverCross, D8) + TP export."""

from __future__ import annotations

import json
from pathlib import Path

from cocotb_coverage.coverage import CoverCross, CoverPoint, coverage_db


@CoverPoint("tp.handshake.kind", xf=lambda kind, hooks: kind, bins=["vr", "vo", "csr", "hook"])
@CoverPoint("tp.netlist.hooks", xf=lambda kind, hooks: hooks, bins=[0, 1])
@CoverCross("tp.handshake_x_hooks", items=["tp.handshake.kind", "tp.netlist.hooks"])
def sample_selfcheck(kind: str, hooks: int) -> None:
    """Hit by the TB self-check. Real TPs live in VERIF_PLAN (PR #3)."""


def export_functional(path: str | Path) -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # YAML if the helper exists; always write JSON for the TP rollup.
    try:
        coverage_db.export_to_yaml(filename=str(dest.with_suffix(".yml")))
    except Exception:
        pass
    payload = {}
    for name, node in coverage_db.items():
        covered = getattr(node, "coverage", None)
        size = getattr(node, "size", None)
        entry = {
            "coverage": covered,
            "size": size,
        }
        detailed = getattr(node, "detailed_coverage", None)
        if detailed:
            entry["detailed"] = _jsonable(detailed)
        payload[name] = entry
    dest.write_text(json.dumps(payload, indent=2) + "\n")


def _jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return str(obj)
