"""Functional coverage scaffold (CoverPoint / CoverCross, D8) + TP export."""

from __future__ import annotations

import json
from pathlib import Path

from cocotb_coverage.coverage import CoverCross, CoverPoint, coverage_db


@CoverPoint("tp.handshake.kind", xf=lambda kind: kind, bins=["vr", "vo", "csr", "hook"])
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
        payload[name] = {
            "coverage": covered,
            "size": size,
        }
    dest.write_text(json.dumps(payload, indent=2) + "\n")
