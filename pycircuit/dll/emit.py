#!/usr/bin/env python3
"""Temporary emit for RETRY_*_SM leaves until PR #5 lands ``scripts/emit_rtl.py``.

PR #5 convention (``git show origin/cursor/rtl-m1-leaf-batch1-e5bb:pycircuit/emit.py``):
  PRODUCT  rtl/<block>/<module>.v
  HOOKS    rtl/<block>/hooks/<module>.v

    python3 pycircuit/dll/emit.py

Do not add ``scripts/emit_rtl.py`` here — that file lands via PR #5 (merges
first). After #5 is on main, merge main and register these leaves in
``pycircuit/emit.py`` / ``scripts/emit_rtl.py`` (PRODUCT + HOOKS), then
delete this wrapper.

Do not put the repo root on PYTHONPATH (the toolchain package is also
named pycircuit).
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYC = HERE.parent
REPO = PYC.parent

if str(PYC) not in sys.path:
    sys.path.insert(0, str(PYC))

from dll.ub_dll_retry_ack_sm import generate as gen_ack  # noqa: E402
from dll.ub_dll_retry_req_sm import generate as gen_req  # noqa: E402


def emit_all() -> list[Path]:
    written: list[Path] = []
    for gen in (gen_req, gen_ack):
        product, hooks = gen()
        written.extend((product, hooks))
    return written


def main() -> int:
    for p in emit_all():
        print(f"wrote {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
