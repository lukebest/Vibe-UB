#!/usr/bin/env python3
"""Emit committed Verilog under rtl/ from pycircuit/<layer>/ leaves.

CSR: compile() + pycc --emit=verilog --logic-depth=64 for every variants: tag
(PRODUCT → rtl/csr/ub_csr_<tag>.v, HOOKS → rtl/csr/hooks/ub_csr_<tag>.v).
This is the path `python3 scripts/gen_regmap.py --check` byte-compares, and
the same entry the gate (PR #14) rtl-emit / provenance regen will invoke.

PHY/DLL (PR #5): same flags; register leaves + variant tables in
pycircuit/emit.py generate() (PRODUCT → rtl/<block>/, HOOKS → rtl/<block>/hooks/).
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def emit_csr() -> list[Path]:
    ns = runpy.run_path(str(REPO_ROOT / "pycircuit" / "csr" / "ub_csr_regs.py"))
    written = ns["generate"]()
    return [Path(p) for p in written]


def emit_phy_dll() -> list[Path]:
    ns = runpy.run_path(str(REPO_ROOT / "pycircuit" / "emit.py"))
    written = ns["generate"]()
    return [Path(p) for p in written]


# Framework owned by PR #11. Each PR appends one generate() entry.
GENERATORS = [
    emit_csr,      # PR #11
    emit_phy_dll,  # PR #5
]


def main() -> int:
    paths: list[Path] = []
    for emit in GENERATORS:
        script = {
            emit_csr: REPO_ROOT / "pycircuit" / "csr" / "ub_csr_regs.py",
            emit_phy_dll: REPO_ROOT / "pycircuit" / "emit.py",
        }[emit]
        if not script.is_file():
            continue
        chunk = emit()
        paths.extend(chunk)
        if emit is emit_csr and len(chunk) != 8:
            print(f"error: expected 8 CSR netlists, wrote {len(chunk)}", file=sys.stderr)
            return 1
    for path in paths:
        try:
            print(f"wrote {path.relative_to(REPO_ROOT)}")
        except ValueError:
            print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
