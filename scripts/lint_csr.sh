#!/usr/bin/env bash
# Emit ub_csr PRODUCT + HOOKS to a temp dir and verilator --lint-only -Wall.
# rtl/csr/*.v is not committed here (scripts/emit_rtl.py / PR #5 follow-up).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 - <<PY
import runpy
from pathlib import Path
ns = runpy.run_path("pycircuit/csr/ub_csr_regs.py")
tmp = Path(r"$TMP")
(tmp / "ub_csr.v").write_text(ns["emit_verilog"](False), encoding="utf-8")
(tmp / "hooks").mkdir()
(tmp / "hooks" / "ub_csr.v").write_text(ns["emit_verilog"](True), encoding="utf-8")
print(f"wrote {tmp / 'ub_csr.v'}")
print(f"wrote {tmp / 'hooks' / 'ub_csr.v'}")
PY
verilator --lint-only -Wall "$TMP/ub_csr.v"
verilator --lint-only -Wall "$TMP/hooks/ub_csr.v"
echo "verilator --lint-only -Wall: PRODUCT + HOOKS clean"
