#!/usr/bin/env python3
"""Emit committed Verilog under rtl/ from pycircuit/<layer>/ leaves.

compile() + pycc --emit=verilog --logic-depth=64. Never assemble pycc
argv elsewhere. CSR / PHY-DLL generators land via #11 / #5; those
entries are skipped when their scripts are not on this branch.

    python3 scripts/emit_rtl.py
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def emit_csr() -> list[Path]:
    ns = runpy.run_path(str(REPO_ROOT / "pycircuit" / "csr" / "ub_csr_regs.py"))
    return [Path(p) for p in ns["generate"]()]


def emit_phy_dll() -> list[Path]:
    ns = runpy.run_path(str(REPO_ROOT / "pycircuit" / "emit.py"))
    return [Path(p) for p in ns["generate"]()]


def emit_lmsm() -> list[Path]:
    ns = runpy.run_path(str(REPO_ROOT / "pycircuit" / "lmsm" / "emit.py"))
    return [Path(p) for p in ns["generate"]()]


# Framework owned by PR #11. Each PR appends one generate() entry.
GENERATORS = [
    ("csr", REPO_ROOT / "pycircuit" / "csr" / "ub_csr_regs.py", emit_csr),
    ("phy_dll", REPO_ROOT / "pycircuit" / "emit.py", emit_phy_dll),
    ("lmsm", REPO_ROOT / "pycircuit" / "lmsm" / "emit.py", emit_lmsm),
]


def main() -> int:
    paths: list[Path] = []
    for _name, script, emit in GENERATORS:
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
