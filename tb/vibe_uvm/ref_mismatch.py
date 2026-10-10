"""Xia: ref vs model/tb.models mismatch — record, do not edit either side."""

from __future__ import annotations

import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEST = REPO / "formal" / "reports" / "ref_vs_model"


def ref_mode() -> bool:
    raw = os.environ.get("REF", "")
    return raw not in ("", "0")


def _stem() -> str:
    leaf = os.environ.get("LEAF", "leaf")
    tag = os.environ.get("REF_TAG", "")
    n = os.environ.get("NUM_LANES", "")
    pol = os.environ.get("PYC_RST_ACTIVE_HIGH", "")
    parts = [leaf]
    if tag:
        parts.append(tag)
    elif leaf.startswith("ub_pcs_lane") and n:
        parts.append(f"x{n}")
    elif leaf == "ub_pyc_rst_adapt" and pol != "":
        parts.append(f"pol{pol}")
    return "_".join(parts)


def record(
    *,
    leaf: str,
    ctx: str,
    expected,
    actual,
    extra: dict | None = None,
) -> Path:
    """Append one mismatch. Never mutates formal/ref or tb/models."""
    DEST.mkdir(parents=True, exist_ok=True)
    path = DEST / f"{_stem()}.json"
    row = {
        "leaf": leaf,
        "ctx": ctx,
        "expected": expected if isinstance(expected, (int, str, list)) else repr(expected),
        "actual": actual if isinstance(actual, (int, str, list)) else repr(actual),
        "seed": int(os.environ.get("COCOTB_RANDOM_SEED", "0") or "0"),
        "note": "Xia: do not edit formal/ref or model/tb.models; SPEC arbitration",
    }
    if extra:
        row.update(extra)
    if isinstance(expected, int) and isinstance(actual, int):
        row["expected_hex"] = hex(expected)
        row["actual_hex"] = hex(actual)
        row["xor_hex"] = hex(expected ^ actual)
    payload = {"mismatches": []}
    if path.exists():
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            payload = {"mismatches": []}
    payload.setdefault("mismatches", []).append(row)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"REF_VS_MODEL mismatch wrote {path} ctx={ctx}", flush=True)
    return path
