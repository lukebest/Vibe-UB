#!/usr/bin/env bash
# Directed PRODUCT smoke (Verilator). Placeholder primitive, not PR #21 RTL.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RTL="$ROOT/rtl/mem"
PYC_LIB="$ROOT/rtl/pyc_lib"
PH="$ROOT/tb/mem/lint_placeholder/ub_cmn_mem_1r1w_d64w109.v"
TB="$ROOT/tb/mem/ub_mem_tlb_inv_smoke_tb.v"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/ub_mem_smoke.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# Strip `include so pyc_reg.v is compiled once (both leaves include it).
grep -v '^`include "pyc_reg.v"' "$RTL/ub_mem_tlb.v" > "$WORK/ub_mem_tlb.v"
grep -v '^`include "pyc_reg.v"' "$RTL/ub_mem_inv.v" > "$WORK/ub_mem_inv.v"
verilator --binary --timing --top-module ub_mem_tlb_inv_smoke_tb \
  -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN -Wno-MODDUP \
  -I"$PYC_LIB" \
  "$PH" \
  "$PYC_LIB/pyc_reg.v" \
  "$WORK/ub_mem_tlb.v" \
  "$WORK/ub_mem_inv.v" \
  "$TB" \
  -Mdir "$WORK/obj" \
  -o smoke

"$WORK/obj/smoke"
echo "SMOKE DONE"
