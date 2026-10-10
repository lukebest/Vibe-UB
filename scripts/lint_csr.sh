#!/usr/bin/env bash
# Emit ub_csr PRODUCT + HOOKS via compile()+pycc and verilator --lint-only -Wall.
# rtl/csr/*.v is not committed here (scripts/emit_rtl.py / PR #5 follow-up).
# GitHub CI has the frontend only (no LLVM/pycc): skip verilator in that case.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYCC_BIN="${PYCC:-}"
if [[ -z "$PYCC_BIN" ]]; then
  PYCC_BIN="$(command -v pycc || true)"
fi
if [[ -z "$PYCC_BIN" ]]; then
  echo "SKIP verilator: pycc not on PATH (D5 Verilog is pycc --emit=verilog / LLVM 19)"
  exit 0
fi

INC_DIR=""
if [[ -n "${PYC_PRIMITIVES:-}" && -d "${PYC_PRIMITIVES}" ]]; then
  INC_DIR="${PYC_PRIMITIVES}"
elif [[ -n "${PYC_TOOLCHAIN_ROOT:-}" && -d "${PYC_TOOLCHAIN_ROOT}/include/verilog" ]]; then
  INC_DIR="${PYC_TOOLCHAIN_ROOT}/include/verilog"
else
  CAND="$(cd "$(dirname "$PYCC_BIN")/../include/verilog" && pwd)"
  if [[ -d "$CAND" ]]; then
    INC_DIR="$CAND"
  elif [[ -d /tmp/pyCircuit/runtime/verilog ]]; then
    INC_DIR="/tmp/pyCircuit/runtime/verilog"
  fi
fi
if [[ -z "$INC_DIR" ]]; then
  echo "error: pycc Verilog primitives dir not found (set PYC_PRIMITIVES or PYC_TOOLCHAIN_ROOT)"
  exit 1
fi

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
print(f"wrote {tmp / 'ub_csr.v'} via pycc")
print(f"wrote {tmp / 'hooks' / 'ub_csr.v'} via pycc")
PY
verilator --lint-only -Wall --top-module ub_csr -I"$INC_DIR" "$TMP/ub_csr.v"
verilator --lint-only -Wall --top-module ub_csr -I"$INC_DIR" "$TMP/hooks/ub_csr.v"
echo "verilator --lint-only -Wall: PRODUCT + HOOKS clean (pycc .v, -I $INC_DIR)"
