#!/usr/bin/env python3
"""Emit committed Verilog under rtl/ from pycircuit/<layer>/ leaves.

CSR: compile() + pycc --emit=verilog --logic-depth=64 for every variants: tag
(PRODUCT → rtl/csr/ub_csr_<tag>.v, HOOKS → rtl/csr/hooks/ub_csr_<tag>.v).
This is the path `python3 scripts/gen_regmap.py --check` byte-compares, and
the same entry the gate (PR #14) rtl-emit / provenance regen will invoke.

Netlists `` `include "pyc_reg.v" `` (SPEC §2.2). They do not copy pyc_*
runtime files into rtl/csr/ or rtl/csr/hooks/. Lint / synth / gate use
`-I rtl/pyc_lib`. That directory is not on main yet; until it lands, local
lint falls back to PYC_TOOLCHAIN_ROOT / pycc include/verilog.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CSR_LEAF = REPO_ROOT / "pycircuit" / "csr" / "ub_csr.py"


def _csr_ns() -> dict:
    return runpy.run_path(str(CSR_LEAF))


def _planned_paths(ns: dict) -> list[Path]:
    paths: list[Path] = []
    for tag in ns["VARIANTS"]:
        paths.append(ns["product_v"](tag))
        paths.append(ns["hooks_v"](tag))
    return paths


def emit_csr() -> list[Path]:
    ns = _csr_ns()
    written = ns["generate"]()
    return [Path(p) for p in written]


def main() -> int:
    if not CSR_LEAF.is_file():
        print(f"error: missing CSR leaf {CSR_LEAF}", file=sys.stderr)
        return 1
    ns = _csr_ns()
    planned = _planned_paths(ns)
    find_pycc = ns.get("_find_pycc")
    if find_pycc is None or not find_pycc():
        missing = [p for p in planned if not Path(p).is_file()]
        if missing:
            print(
                "error: pycc not on PATH and committed CSR netlists missing:",
                file=sys.stderr,
            )
            for path in missing:
                print(f"  {path}", file=sys.stderr)
            return 1
        print(
            "emit_rtl: pycc not on PATH; leaving committed rtl/csr netlists "
            "unchanged (gate rtl-emit-consistency then git-diffs a no-op). "
            "Netlists `include \"pyc_reg.v\"; lint/synth use -I rtl/pyc_lib "
            "(not on main yet)."
        )
        for path in planned:
            try:
                print(f"kept {path.relative_to(REPO_ROOT)}")
            except ValueError:
                print(f"kept {path}")
        if len(planned) != 8:
            print(f"error: expected 8 CSR netlists, found {len(planned)}", file=sys.stderr)
            return 1
        return 0

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
