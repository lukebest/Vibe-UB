#!/usr/bin/env python3
"""Emit committed Verilog under rtl/ from pycircuit/<layer>/ leaves.

compile() + pycc --emit=verilog --logic-depth=64. Gate
rtl_emit_consistency invokes this script and never assembles pycc argv.

This PR registers only the two RETRY_*_SM leaves. PR #5 / #11 append
their generate() entries when those sources are on the tree.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYC = REPO_ROOT / "pycircuit"

if str(PYC) not in sys.path:
    sys.path.insert(0, str(PYC))


def emit_retry_sms() -> list[Path]:
    from dll.ub_dll_retry_ack_sm import generate as gen_ack
    from dll.ub_dll_retry_req_sm import generate as gen_req

    written: list[Path] = []
    for gen in (gen_req, gen_ack):
        product, hooks = gen()
        written.extend((product, hooks))
    return written


def emit_csr() -> list[Path]:
    ns = runpy.run_path(str(REPO_ROOT / "pycircuit" / "csr" / "ub_csr_regs.py"))
    return [Path(p) for p in ns["generate"]()]


def emit_phy_dll() -> list[Path]:
    ns = runpy.run_path(str(REPO_ROOT / "pycircuit" / "emit.py"))
    return [Path(p) for p in ns["generate"]()]


def main() -> int:
    paths: list[Path] = []
    paths.extend(emit_retry_sms())
    for script, emit in (
        (REPO_ROOT / "pycircuit" / "csr" / "ub_csr_regs.py", emit_csr),
        (REPO_ROOT / "pycircuit" / "emit.py", emit_phy_dll),
    ):
        if not script.is_file():
            continue
        paths.extend(emit())
    for path in paths:
        try:
            print(f"wrote {path.relative_to(REPO_ROOT)}")
        except ValueError:
            print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
