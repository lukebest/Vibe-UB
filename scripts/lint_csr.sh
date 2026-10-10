#!/usr/bin/env bash
# Emit ub_csr PRODUCT + HOOKS via compile()+pycc and verilator --lint-only -Wall
# for every variants: tag (SPEC §2.2 module ub_csr_<tag>).
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
(tmp / "hooks").mkdir()
for tag in ns["VARIANTS"]:
    mod = ns["csr_module_name"](tag)
    (tmp / f"{mod}.v").write_text(ns["emit_verilog"](False, variant=tag), encoding="utf-8")
    (tmp / "hooks" / f"{mod}.v").write_text(ns["emit_verilog"](True, variant=tag), encoding="utf-8")
    print(f"wrote {tmp / (mod + '.v')} via pycc")
    print(f"wrote {tmp / 'hooks' / (mod + '.v')} via pycc")
PY

shopt -s nullglob
for vfile in "$TMP"/ub_csr_*.v; do
  mod="$(basename "$vfile" .v)"
  verilator --lint-only -Wall --top-module "$mod" -I"$INC_DIR" "$vfile"
  verilator --lint-only -Wall --top-module "$mod" -I"$INC_DIR" "$TMP/hooks/$mod.v"
  echo "verilator --lint-only -Wall: $mod PRODUCT + HOOKS clean (pycc .v, -I $INC_DIR)"
done
echo "verilator --lint-only -Wall: all variants clean"
