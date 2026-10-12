#!/usr/bin/env bash
# Directed PRODUCT smoke (Verilator). Placeholder primitive, not PR #21 RTL.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RTL="$ROOT/rtl/mem"
PH="$ROOT/tb/mem/lint_placeholder/ub_cmn_mem_1r1w_d64w109.v"
TB="$ROOT/tb/mem/ub_mem_tlb_inv_smoke_tb.v"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/ub_mem_smoke.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# `-I rtl/pyc_lib` (SPEC §2.2). Fail until #21 lands; do not fetch it.
PYC_INC="$ROOT/rtl/pyc_lib"
PYC_REG="$PYC_INC/pyc_reg.v"
if [[ ! -f "$PYC_REG" ]]; then
  echo "missing rtl/pyc_lib/pyc_reg.v — depends on PR #21"
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

echo "=== ptw smoke ==="
bash "$ROOT/tb/mem/run_ptw_smoke.sh"
