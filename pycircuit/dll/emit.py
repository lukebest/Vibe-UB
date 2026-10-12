#!/usr/bin/env python3
"""Emit RETRY_*_SM PRODUCT + HOOKS (pycircuit → pycc).

    PYTHONPATH=pycircuit python3 -P pycircuit/dll/emit.py

scripts/emit_rtl.py is the gate entry and calls the same generate().
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
