#!/usr/bin/env python3
"""Emit PRODUCT Verilog (TEST_HOOKS=0) from pycircuit sources.

CODING_STYLE §1: submitted .v must be reproducible from current Python.
`pycc` (MLIR → Verilog) is used when present; the committed netlist is
always written by this emitter so LLVM 19 is not required.

Layout (SPEC §2.2 / CODING_STYLE §5; same as PR #7 ub_lmsm):
  PRODUCT  rtl/<block>/<module>.v
  HOOKS    rtl/<block>/hooks/<module>.v   (not emitted here — SPEC §10
           lists no hooks on these leaves, so PRODUCT is the only netlist)
Whitelist SV is handwritten: rtl/common/ub_rst_sync.sv
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
RTL = REPO / "rtl"

# pycircuit/ on sys.path — do NOT put REPO root on PYTHONPATH (shadows
# the toolchain package also named pycircuit).
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.ub_pyc_rst_adapt import emit_verilog as emit_rst_adapt
from dll.ub_dll_bcrc import emit_verilog as emit_bcrc
from dll.ub_dll_bcrc_check import emit_verilog as emit_bcrc_check
from pcs.ub_pcs_descrambler import emit_verilog as emit_descrambler
from pcs.ub_pcs_lane_dedist import emit_verilog as emit_dedist
from pcs.ub_pcs_lane_dist import emit_verilog as emit_dist
from pcs.ub_pcs_scrambler import emit_verilog as emit_scrambler

LEAVES = (
    ("common", "ub_pyc_rst_adapt", emit_rst_adapt),
    ("pcs", "ub_pcs_scrambler", emit_scrambler),
    ("pcs", "ub_pcs_descrambler", emit_descrambler),
    ("pcs", "ub_pcs_lane_dist", emit_dist),
    ("pcs", "ub_pcs_lane_dedist", emit_dedist),
    ("dll", "ub_dll_bcrc", emit_bcrc),
    ("dll", "ub_dll_bcrc_check", emit_bcrc_check),
)


def emit_all(out_root: Path = RTL) -> list[Path]:
    written: list[Path] = []
    for layer, name, fn in LEAVES:
        dest = out_root / layer / f"{name}.v"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(fn(), encoding="utf-8")
        written.append(dest)
    return written


def try_pycc() -> str:
    """Best-effort: note whether pycc is present. Does not replace emit()."""
    pycc = shutil.which("pycc")
    if pycc is None:
        return "pycc: not on PATH (LLVM 19 toolchain not required for make emit)"
    try:
        ver = subprocess.check_output([pycc, "--version"], text=True, timeout=10)
        return f"pycc: {ver.strip()} (optional; PRODUCT .v still from make emit)"
    except (subprocess.SubprocessError, OSError) as exc:
        return f"pycc: found but failed ({exc})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RTL)
    args = parser.parse_args()
    paths = emit_all(args.out)
    print(try_pycc())
    for p in paths:
        print(f"wrote {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
