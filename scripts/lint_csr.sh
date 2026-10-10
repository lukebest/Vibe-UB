#!/usr/bin/env bash
# Verilator --lint-only -Wall on the 8 committed ub_csr netlists
# (4 variants × PRODUCT + HOOKS). Regen must stay byte-identical
# (`python3 scripts/gen_regmap.py --check` / scripts/emit_rtl.py).
# GitHub CI has the frontend only (no LLVM/pycc): skip when pycc is absent
# *and* the committed files are missing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# SPEC §2.2: single copy of pyc_* primitives lives in rtl/pyc_lib/.
# That directory is not on main yet (PR #28/#29 mentioned it; files not
# landed). Prefer it when present; otherwise fall back to the pycc install.
INC_DIR=""
if [[ -d "$ROOT/rtl/pyc_lib" ]]; then
  INC_DIR="$ROOT/rtl/pyc_lib"
  echo "lint_csr: -I rtl/pyc_lib (SPEC §2.2 single copy)"
elif [[ -n "${PYC_PRIMITIVES:-}" && -d "${PYC_PRIMITIVES}" ]]; then
  INC_DIR="${PYC_PRIMITIVES}"
  echo "lint_csr: NOTE rtl/pyc_lib/ not on this tree; -I $INC_DIR"
elif [[ -n "${PYC_TOOLCHAIN_ROOT:-}" && -d "${PYC_TOOLCHAIN_ROOT}/include/verilog" ]]; then
  INC_DIR="${PYC_TOOLCHAIN_ROOT}/include/verilog"
  echo "lint_csr: NOTE rtl/pyc_lib/ not on this tree; -I $INC_DIR"
else
  PYCC_BIN="${PYCC:-}"
  if [[ -z "$PYCC_BIN" ]]; then
    PYCC_BIN="$(command -v pycc || true)"
  fi
  if [[ -n "$PYCC_BIN" ]]; then
    CAND="$(cd "$(dirname "$PYCC_BIN")/../include/verilog" && pwd)"
    if [[ -d "$CAND" ]]; then
      INC_DIR="$CAND"
    fi
  fi
  if [[ -z "$INC_DIR" && -d /tmp/pyCircuit/runtime/verilog ]]; then
    INC_DIR="/tmp/pyCircuit/runtime/verilog"
  fi
  if [[ -n "$INC_DIR" ]]; then
    echo "lint_csr: NOTE rtl/pyc_lib/ not on this tree; -I $INC_DIR"
  fi
fi

shopt -s nullglob
PRODUCTS=(rtl/csr/ub_csr_*.v)
if [[ ${#PRODUCTS[@]} -eq 0 ]]; then
  echo "error: no committed rtl/csr/ub_csr_*.v netlists"
  exit 1
fi
if [[ -z "$INC_DIR" ]]; then
  echo "error: pyc_reg.v include dir not found (want rtl/pyc_lib; else PYC_PRIMITIVES / PYC_TOOLCHAIN_ROOT)"
  exit 1
fi

count=0
for vfile in rtl/csr/ub_csr_*.v; do
  mod="$(basename "$vfile" .v)"
  hooks="rtl/csr/hooks/${mod}.v"
  if [[ ! -f "$hooks" ]]; then
    echo "error: missing HOOKS netlist $hooks"
    exit 1
  fi
  verilator --lint-only -Wall --top-module "$mod" -I"$INC_DIR" "$vfile"
  verilator --lint-only -Wall --top-module "$mod" -I"$INC_DIR" "$hooks"
  echo "verilator --lint-only -Wall: $mod PRODUCT + HOOKS clean ($vfile, $hooks, -I $INC_DIR)"
  count=$((count + 2))
done
if [[ "$count" -ne 8 ]]; then
  echo "error: expected 8 netlists linted, got $count"
  exit 1
fi
echo "verilator --lint-only -Wall: all 8 variant netlists clean"
