#!/usr/bin/env python3
"""Public-tree check for S-01(b) contracts, stubs, and attests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import emit_report
from private_leaves import collect_contract_findings


def main() -> int:
    return emit_report("contract", collect_contract_findings())


if __name__ == "__main__":
    raise SystemExit(main())
