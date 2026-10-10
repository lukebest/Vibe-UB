#!/usr/bin/env python3
"""Emit PRODUCT + HOOKS Verilog from registered pycircuit leaves.

CODING_STYLE §1 / SPEC §11: TEST_HOOKS expands at Python generation time.
  PRODUCT  TEST_HOOKS=0  → rtl/<block>/<module>.v
  HOOKS    TEST_HOOKS=1  → rtl/<block>/hooks/<module>.v

SPEC §10 lists no hook ports on this batch, so HOOKS is port-identical
to PRODUCT (header ``TEST_HOOKS=1`` only). Xia: do not add unused
``tb_test_mode`` (that is only for modules §10 lists hooks for).

Layers register via ``lib.registry.register``. Batch-1 registers here;
later ``pycircuit/lmsm``, extra ``pycircuit/dll``, ``pycircuit/csr``
call ``register()`` from ``scripts/emit_rtl.py``.

Whitelist SV is handwritten: rtl/common/ub_rst_sync.sv — no HOOKS copy
(CODING_STYLE §3 does not require one).

Do not put the repo root on PYTHONPATH (toolchain package is also
named pycircuit).
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

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.ub_pyc_rst_adapt import emit_verilog as emit_rst_adapt
from dll.ub_dll_bcrc import emit_verilog as emit_bcrc
from dll.ub_dll_bcrc_check import emit_verilog as emit_bcrc_check
from lib.registry import Leaf, register, registered
from pcs.ub_pcs_descrambler import emit_verilog as emit_descrambler
from pcs.ub_pcs_lane_dedist import emit_verilog as emit_dedist
from pcs.ub_pcs_lane_dist import emit_verilog as emit_dist
from pcs.ub_pcs_scrambler import emit_verilog as emit_scrambler


def register_batch1() -> None:
    """M1 leaf batch 1. Idempotent."""
    register("common", "ub_pyc_rst_adapt", emit_rst_adapt)
    register("pcs", "ub_pcs_scrambler", emit_scrambler)
    register("pcs", "ub_pcs_descrambler", emit_descrambler)
    register("pcs", "ub_pcs_lane_dist", emit_dist)
    register("pcs", "ub_pcs_lane_dedist", emit_dedist)
    register("dll", "ub_dll_bcrc", emit_bcrc)
    register("dll", "ub_dll_bcrc_check", emit_bcrc_check)


def write_leaf(leaf: Leaf, out_root: Path = RTL) -> list[Path]:
    product = out_root / leaf.layer / f"{leaf.name}.v"
    hooks = out_root / leaf.layer / "hooks" / f"{leaf.name}.v"
    product.parent.mkdir(parents=True, exist_ok=True)
    hooks.parent.mkdir(parents=True, exist_ok=True)
    product.write_text(leaf.emit(test_hooks=False), encoding="utf-8")
    hooks.write_text(leaf.emit(test_hooks=True), encoding="utf-8")
    return [product, hooks]


def emit_all(out_root: Path = RTL) -> list[Path]:
    register_batch1()
    written: list[Path] = []
    for leaf in registered():
        written.extend(write_leaf(leaf, out_root))
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
