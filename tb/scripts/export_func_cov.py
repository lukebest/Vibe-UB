#!/usr/bin/env python3
"""Export cocotb-coverage database if a sim left one in-process; else copy JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tb.uvm.coverage import export_functional


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("-o", "--out", default="tb/reports/cov_func/manual.json")
    args = p.parse_args()
    export_functional(args.out)
    dest = Path(args.out)
    if dest.exists():
        print(json.dumps({"wrote": str(dest)}, indent=2))


if __name__ == "__main__":
    main()
