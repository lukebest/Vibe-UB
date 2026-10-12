#!/usr/bin/env bash
# Directed HOOKS smoke for ub_mem_ptw (obs ports on HOOKS only).
# Success cases swap in tb/mem/ub_mem_ptw_desc_dec_tb_model.v (TB protocol).
# Stub cases keep the public placeholder (always translation-fault).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RTL="$ROOT/rtl/mem"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/ub_mem_ptw_smoke.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

PYC_INC="$ROOT/rtl/pyc_lib"
PYC_REG="$PYC_INC/pyc_reg.v"
if [[ ! -f "$PYC_REG" ]]; then
  echo "missing rtl/pyc_lib/pyc_reg.v — depends on PR #21"
  exit 1
fi

# TODO: switch to scripts/gate/gen_private_stub.py once #47 is on main.
PY="${PY:-/tmp/spike/venv/bin/python3}"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi
STUB_V="$WORK/ub_mem_ptw_desc_dec.v"
"$PY" "$ROOT/scripts/gen_ptw_desc_dec_stub.py" --out "$STUB_V"
grep -v '^`include "pyc_reg.v"' "$STUB_V" > "$WORK/stub_ninc.v"
grep -v '^`include "pyc_reg.v"' "$RTL/hooks/ub_mem_ptw.v" > "$WORK/ub_mem_ptw_hooks.v"

echo "=== functional smoke (TB decoder model) ==="
verilator --binary --timing --top-module ub_mem_ptw_smoke_tb \
  -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN -Wno-MODDUP -Wno-WIDTHTRUNC \
  -I"$PYC_INC" \
  "$PYC_REG" \
  "$WORK/ub_mem_ptw_hooks.v" \
  "$ROOT/tb/mem/ub_mem_ptw_desc_dec_tb_model.v" \
  "$ROOT/tb/mem/ub_mem_ptw_smoke_tb.v" \
  -Mdir "$WORK/obj_fn" \
  -o smoke_fn
"$WORK/obj_fn/smoke_fn"

echo "=== stub smoke (public placeholder) ==="
verilator --binary --timing --top-module ub_mem_ptw_stub_smoke_tb \
  -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN -Wno-MODDUP -Wno-WIDTHTRUNC \
  -I"$PYC_INC" \
  "$PYC_REG" \
  "$WORK/ub_mem_ptw_hooks.v" \
  "$WORK/stub_ninc.v" \
  "$ROOT/tb/mem/ub_mem_ptw_stub_smoke_tb.v" \
  -Mdir "$WORK/obj_stub" \
  -o smoke_stub
"$WORK/obj_stub/smoke_stub"

echo "PTW SMOKE DONE"
