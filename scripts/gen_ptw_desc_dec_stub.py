#!/usr/bin/env python3
"""Emit ub_mem_ptw_desc_dec placeholder Verilog to a dest path (tmp/build).

Invokes pycircuit on pycircuit/mem/stub/ub_mem_ptw_desc_dec.py. Do not
write the result under rtl/.

TODO: switch to scripts/gate/gen_private_stub.py once #47 is on main.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PYC = REPO / "pycircuit"
if str(PYC) not in sys.path:
    sys.path.insert(0, str(PYC))

from emit import _find_pycc, emit_one  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    dest = args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    emit_one(
        source=PYC / "mem" / "stub" / "ub_mem_ptw_desc_dec.py",
        module="ub_mem_ptw_desc_dec",
        dest=dest,
        pycc=_find_pycc(),
        test_hooks=0,
        extra={},
    )
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
