#!/usr/bin/env python3
"""Emit PRODUCT + HOOKS Verilog.

Migrated STEP 1 leaves go through compile() + pycc --emit=verilog --logic-depth=64.
Scrambler / descrambler stay on the leftover f-string emitters (STEP 2).

  PRODUCT  TEST_HOOKS=0  → rtl/<block>/<module>.v
  HOOKS    TEST_HOOKS=1  → rtl/<block>/hooks/<module>.v

SPEC §10 lists no hook ports on this batch, so HOOKS is port-identical
to PRODUCT. Xia: do not add unused tb_test_mode.

Whitelist SV is handwritten: rtl/common/ub_rst_sync.sv — no HOOKS copy.
Do not put the repo root on PYTHONPATH (toolchain package is also named
pycircuit).
"""

from __future__ import annotations

import argparse
import os
import shutil
import site
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
RTL = REPO / "rtl"

os.environ.setdefault(
    "PYC_TOOLCHAIN_ROOT",
    "/tmp/pyCircuit/.pycircuit_out/toolchain/install",
)
_root = Path(os.environ["PYC_TOOLCHAIN_ROOT"])
os.environ["PATH"] = f"{_root / 'bin'}:{os.environ.get('PATH', '')}"
_venv = Path(os.environ.get("UB_PYC_VENV", "/tmp/venv"))
for _site in _venv.glob("lib/python*/site-packages"):
    site.addsitedir(str(_site))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common import ub_pyc_rst_adapt as rst_adapt
from dll import ub_dll_bcrc as bcrc
from dll import ub_dll_bcrc_check as bcrc_check
from lib.pycc_emit import emit_variant, toolchain_root
from lib.registry import Leaf, register, registered
from lib.variants import variant_name
from pcs import ub_pcs_lane_dedist as lane_dedist
from pcs import ub_pcs_lane_dist as lane_dist
from pcs.ub_pcs_descrambler import emit_verilog as emit_descrambler
from pcs.ub_pcs_scrambler import emit_verilog as emit_scrambler

# (layer, module, build, VARIANTS, sequential)
PYC_LEAVES = (
    ("common", rst_adapt.LEAF, rst_adapt.build, rst_adapt.VARIANTS, False),
    ("pcs", lane_dist.LEAF, lane_dist.build, lane_dist.VARIANTS, False),
    ("pcs", lane_dedist.LEAF, lane_dedist.build, lane_dedist.VARIANTS, False),
    ("dll", bcrc.LEAF, bcrc.build, bcrc.VARIANTS, True),
    ("dll", bcrc_check.LEAF, bcrc_check.build, bcrc_check.VARIANTS, True),
)


def _emit_pyc(layer: str, leaf: str, build, tag: str, params: dict, sequential: bool):
    def _fn(test_hooks: bool = False, _p=params, _t=tag, _s=sequential) -> str:
        _name, text = emit_variant(
            build,
            leaf=leaf,
            tag=_t,
            params=_p,
            test_hooks=test_hooks,
            sequential=_s,
        )
        return text

    return _fn


def register_batch1() -> None:
    """M1 leaf batch 1. Idempotent."""
    for layer, leaf, build, variants, sequential in PYC_LEAVES:
        for tag, params in variants.items():
            name = variant_name(leaf, tag)
            register(layer, name, _emit_pyc(layer, leaf, build, tag, params, sequential))
    # STEP 2 pending: leftover f-string emitters, files untouched.
    register("pcs", "ub_pcs_scrambler", emit_scrambler)
    register("pcs", "ub_pcs_descrambler", emit_descrambler)


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


def generate():
    """PR #5 registration: PHY/DLL STEP 1 variant tables → PRODUCT + HOOKS.

    Same contract as pycircuit/csr/ub_csr_regs.py generate() (PR #11).
    """
    return emit_all()


def try_pycc() -> str:
    pycc = shutil.which("pycc")
    if pycc is None:
        cand = toolchain_root() / "bin" / "pycc"
        pycc = str(cand) if cand.is_file() else None
    if pycc is None:
        return "pycc: not on PATH (run scripts/setup_pycircuit.sh)"
    try:
        ver = subprocess.check_output([pycc, "--version"], text=True, timeout=10)
        return f"pycc: {ver.strip()}"
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
