#!/usr/bin/env bash
# Directed PRODUCT smoke (Verilator). Placeholder primitive, not PR #21 RTL.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RTL="$ROOT/rtl/mem"
PH="$ROOT/tb/mem/lint_placeholder/ub_cmn_mem_1r1w_d64w109.v"
TB="$ROOT/tb/mem/ub_mem_tlb_inv_smoke_tb.v"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/ub_mem_smoke.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# `-I rtl/pyc_lib` after #21. Before that, fetch #21's file outside rtl/.
PR21_REF="${PR21_REF:-origin/cursor/cmn-mem-1r1w-5d26}"
if [[ -f "$ROOT/rtl/pyc_lib/pyc_reg.v" ]]; then
  PYC_INC="$ROOT/rtl/pyc_lib"
else
  git -C "$ROOT" cat-file -e "${PR21_REF}:rtl/pyc_lib/pyc_reg.v" 2>/dev/null \
    || git -C "$ROOT" fetch origin cursor/cmn-mem-1r1w-5d26
  mkdir -p "$WORK/pyc_lib"
  git -C "$ROOT" show "${PR21_REF}:rtl/pyc_lib/pyc_reg.v" > "$WORK/pyc_lib/pyc_reg.v"
  PYC_INC="$WORK/pyc_lib"
fi
PYC_REG="$PYC_INC/pyc_reg.v"
if [[ ! -f "$PYC_REG" ]]; then
  echo "FAIL: pyc_reg.v not found (need #21 rtl/pyc_lib or fetch $PR21_REF)"
  exit 1
fi

# Strip `include so pyc_reg.v is compiled once (both leaves include it).
grep -v '^`include "pyc_reg.v"' "$RTL/ub_mem_tlb.v" > "$WORK/ub_mem_tlb.v"
grep -v '^`include "pyc_reg.v"' "$RTL/ub_mem_inv.v" > "$WORK/ub_mem_inv.v"
verilator --binary --timing --top-module ub_mem_tlb_inv_smoke_tb \
  -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN -Wno-MODDUP \
  -I"$PYC_INC" \
  "$PH" \
  "$PYC_REG" \
  "$WORK/ub_mem_tlb.v" \
  "$WORK/ub_mem_inv.v" \
  "$TB" \
  -Mdir "$WORK/obj" \
  -o smoke

"$WORK/obj/smoke"
echo "SMOKE DONE"
