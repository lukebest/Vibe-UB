#!/usr/bin/env python3
"""Emit committed Verilog under rtl/ from pycircuit/<layer>/ leaves.

CSR: compile() + pycc --emit=verilog --logic-depth=64 for every variants: tag
(PRODUCT → rtl/csr/ub_csr_<tag>.v, HOOKS → rtl/csr/hooks/ub_csr_<tag>.v).
This is the path `python3 scripts/gen_regmap.py --check` byte-compares, and
the same entry the gate (PR #14) rtl-emit / provenance regen will invoke.
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


def main() -> int:
    paths = emit_csr()
    for path in paths:
        try:
            print(f"wrote {path.relative_to(REPO_ROOT)}")
        except ValueError:
            print(f"wrote {path}")
    if len(paths) != 8:
        print(f"error: expected 8 CSR netlists, wrote {len(paths)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
