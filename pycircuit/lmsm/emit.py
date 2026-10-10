#!/usr/bin/env python3
"""Temporary LMSM emit until scripts/emit_rtl.py lands via PR #5.

    python3 pycircuit/lmsm/emit.py

Writes PRODUCT and HOOKS under rtl/lmsm/ (SPEC §2.2 / CODING_STYLE §5;
same layout as PR #5). After #5 is on main, register ``ub_lmsm`` in
``scripts/emit_rtl.py`` / ``pycircuit/emit.py`` (PRODUCT + HOOKS) and
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

from lmsm.ub_lmsm import generate  # noqa: E402


def main() -> int:
    product, hooks = generate()
    print(f"wrote {product.relative_to(REPO)}")
    print(f"wrote {hooks.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
