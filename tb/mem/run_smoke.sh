#!/usr/bin/env bash
# Directed PRODUCT smoke (Verilator). Primitive RTL is owned by PR #21.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RTL="$ROOT/rtl/mem"
TB="$ROOT/tb/mem/ub_mem_tlb_inv_smoke_tb.v"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/ub_mem_smoke.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# Only the working-tree file. Do not fetch from another ref or the toolchain.
# PR #21 owns rtl/pyc_lib/; expected FAIL until that PR lands.
PYC_INC="$ROOT/rtl/pyc_lib"
PYC_REG="$PYC_INC/pyc_reg.v"
if [[ ! -f "$PYC_REG" ]]; then
  echo "FAIL: $PYC_REG missing (owned by PR #21; expected until #21 lands)"
  exit 1
fi

# Strip `include so pyc_reg.v is compiled once (both leaves include it).
grep -v '^`include "pyc_reg.v"' "$RTL/ub_mem_tlb.v" > "$WORK/ub_mem_tlb.v"
grep -v '^`include "pyc_reg.v"' "$RTL/ub_mem_inv.v" > "$WORK/ub_mem_inv.v"
verilator --binary --timing --top-module ub_mem_tlb_inv_smoke_tb \
  -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN -Wno-MODDUP \
  -I"$PYC_INC" \
  "$PYC_REG" \
  "$WORK/ub_mem_tlb.v" \
  "$WORK/ub_mem_inv.v" \
  "$TB" \
  -Mdir "$WORK/obj" \
  -o smoke

"$WORK/obj/smoke"
echo "SMOKE DONE"
