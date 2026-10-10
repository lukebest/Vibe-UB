#!/usr/bin/env python3
"""Emit PRODUCT netlists for registered leaves.

    python3 scripts/emit_rtl.py

Do not put the repo root on PYTHONPATH (the toolchain package is also
named pycircuit).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PYC = REPO / "pycircuit"
if str(PYC) not in sys.path:
    sys.path.insert(0, str(PYC))

from emit import RTL, emit_all  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RTL)
    args = parser.parse_args()
    paths = emit_all(args.out)
    for p in paths:
        try:
            print(f"wrote {p.relative_to(REPO)}")
        except ValueError:
            print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
