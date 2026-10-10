#!/usr/bin/env python3
"""Emit PRODUCT + HOOKS for every registered leaf.

    python3 scripts/emit_rtl.py

Layout (SPEC §2.2 / CODING_STYLE §5; same as PR #7 ``ub_lmsm``):

    PRODUCT  rtl/<block>/<module>.v
    HOOKS    rtl/<block>/hooks/<module>.v

Register later layers here (emit callable must take ``test_hooks: bool``):

    from lmsm.ub_lmsm import emit_verilog as emit_lmsm
    register("lmsm", "ub_lmsm", emit_lmsm)

    from dll.ub_dll_credit import emit_verilog as emit_credit
    register("dll", "ub_dll_credit", emit_credit)

    from csr.ub_csr import emit_verilog as emit_csr
    register("csr", "ub_csr", emit_csr)

Do not put the repo root on PYTHONPATH (the toolchain package is also
named pycircuit). Whitelist ``rtl/common/ub_rst_sync.sv`` is handwritten
and is not copied into ``hooks/`` (CODING_STYLE §3).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PYC = REPO / "pycircuit"
if str(PYC) not in sys.path:
    sys.path.insert(0, str(PYC))

from emit import emit_all, register_batch1, try_pycc  # noqa: E402
from lib.registry import register  # noqa: E402, F401  — public for later layers


def main() -> int:
    register_batch1()
    # Later layers (uncomment when those emitters exist):
    # from lmsm.ub_lmsm import emit_verilog as emit_lmsm
    # register("lmsm", "ub_lmsm", emit_lmsm)
    # from dll.ub_dll_credit import emit_verilog as emit_credit
    # register("dll", "ub_dll_credit", emit_credit)
    # from csr.ub_csr import emit_verilog as emit_csr
    # register("csr", "ub_csr", emit_csr)
    paths = emit_all()
    print(try_pycc())
    for p in paths:
        print(f"wrote {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
