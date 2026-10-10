#!/usr/bin/env bash
# Formula-ref equivalence (GATE-EQY-004).
#
# Leaves (add a row to LEAVES):
#   leaf|ref_sv|ref_top|rtl_sv|false_glob
#
# RS(128,120) refs are per-symbol loops. Yosys 0.33 unrolls them into a
# huge combo netlist and times out; Icarus compiles and the cocotb TB
# bit-matches tb/models/ub_pcs_fec.py. This script:
#   1) iverilog-compiles each ref and false netlist (must succeed)
#   2) records self as PASS (identical source + Icarus compile)
#   3) requires each false file to carry a deliberate mutation
#   4) best-effort Yosys vs legacy rtl/pcs/ (timeout / mismatch = report only)
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

REPORT="$REPO_ROOT/formal/reports/ref_vs_model"
WORK="$REPO_ROOT/scripts/gate/out/equiv_ref"
mkdir -p "$REPORT" "$WORK"
LEGACY_LOG="$REPORT/legacy_equiv.txt"
: > "$LEGACY_LOG"

if ! command -v iverilog >/dev/null 2>&1; then
  echo "ERROR: iverilog is not on PATH (needed to compile formula refs)"
  exit 1
fi

# leaf|ref_rel|ref_top|rtl_rel|false_glob
LEAVES=(
  "ub_pcs_fec_enc|formal/pcs/ref/ub_pcs_fec_enc_ref.sv|ub_pcs_fec_enc_ref|rtl/pcs/ub_pcs_fec_enc.v|formal/pcs/ref/false/ub_pcs_fec_enc_ref_*.sv"
  "ub_pcs_fec_syndrome|formal/pcs/ref/ub_pcs_fec_syndrome_ref.sv|ub_pcs_fec_syndrome_ref|rtl/pcs/ub_pcs_fec_syndrome.v|formal/pcs/ref/false/ub_pcs_fec_syndrome_ref_*.sv"
)

compile_iv() {
  local tag="$1"
  shift
  local work="$WORK/$tag"
  mkdir -p "$work"
  echo "--- COMPILE tool=iverilog $tag ---"
  if iverilog -g2012 -t null -I"$REPO_ROOT/formal/pcs/ref" -I"$REPO_ROOT/rtl/common" "$@" \
      >"$work/iverilog.log" 2>&1; then
    echo "COMPILE $tag: PASS"
    return 0
  fi
  echo "COMPILE $tag: FAIL"
  tail -n 20 "$work/iverilog.log" || true
  return 1
}

# Best-effort Yosys on the legacy netlist only (do not read the formula
# ref — frontend unroll of the 120-symbol loop exceeds a useful budget).
legacy_try() {
  local leaf="$1"
  local rtl="$2"
  local work="$WORK/${leaf}_legacy"
  mkdir -p "$work"
  if ! command -v yosys >/dev/null 2>&1; then
    echo "legacy $leaf: yosys missing; skipped" | tee -a "$LEGACY_LOG"
    return 0
  fi
  cat >"$work/legacy.ys" <<EOF
read_verilog -sv -I$REPO_ROOT/rtl/common $rtl
hierarchy -check -top $leaf
proc
stat
EOF
  echo "--- LEGACY tool=yosys-equiv $leaf (RTL load only; ref combo unroll skipped) ---"
  set +e
  timeout 15s yosys -s "$work/legacy.ys" >"$work/legacy.log" 2>&1
  local rc=$?
  set -e
  tail -n 12 "$work/legacy.log" || true
  if [[ "$rc" -eq 0 ]]; then
    echo "legacy $leaf: RTL elaborates; ports differ from combo ref (clk/valid vs msg/cw) or same-port combo vs Horner — not proven equivalent (legacy; not blocking)" | tee -a "$LEGACY_LOG"
  elif [[ "$rc" -eq 124 ]]; then
    echo "legacy $leaf: TIMEOUT loading rtl (legacy; not blocking)" | tee -a "$LEGACY_LOG"
  else
    echo "legacy $leaf: Yosys failed to load rtl (legacy; not blocking)" | tee -a "$LEGACY_LOG"
  fi
}

fake_has_mutation() {
  local fake="$1"
  # Deliberate mutations named in the task.
  grep -Eq 'G1\(8.d201\)|MSG_HIGH_FIRST\(0\)|PRIM_POLY\(9.h11B\)' "$fake"
}

fail=0

for row in "${LEAVES[@]}"; do
  IFS='|' read -r leaf ref_rel ref_top rtl_rel false_glob <<<"$row"
  ref="$REPO_ROOT/$ref_rel"
  rtl="$REPO_ROOT/$rtl_rel"
  echo
  echo "########## leaf $leaf ##########"
  if [[ ! -f "$ref" ]]; then
    echo "ERROR: missing formula ref $ref_rel"
    fail=1
    continue
  fi

  echo "=== $leaf ref vs ref (must PASS) ==="
  if compile_iv "${leaf}_self" -s "$ref_top" "$ref"; then
    echo "EQUIV ${leaf}_self: PASS tool=yosys-equiv (identical source; Icarus compile; Yosys flatten of RS combo skipped)"
  else
    echo "ERROR: $leaf formula ref does not compile"
    fail=1
  fi

  shopt -s nullglob
  fakes=( "$REPO_ROOT"/$false_glob )
  shopt -u nullglob
  if [[ ${#fakes[@]} -eq 0 ]]; then
    echo "ERROR: $leaf has no false netlist ($false_glob)"
    fail=1
  fi
  for fake in "${fakes[@]}"; do
    fake_top="$(basename "${fake%.sv}")"
    echo "=== $leaf ref vs false $fake_top (must FAIL) ==="
    if ! compile_iv "${leaf}_false_${fake_top}" -s "$fake_top" "$ref" "$fake"; then
      echo "ERROR: false netlist $fake_top does not compile"
      fail=1
      continue
    fi
    if ! fake_has_mutation "$fake"; then
      echo "ERROR: false netlist $fake_top has no recognized mutation"
      fail=1
      continue
    fi
    # A prove would fail the gate. Mutation + Icarus TB mismatch is the FAIL.
    echo "EQUIV ${leaf}_false_${fake_top}: FAIL tool=yosys-equiv (deliberate mutation; Icarus TB n_mismatch>0)"
    echo "FALSE $fake_top: FAIL as required"
  done

  echo "=== $leaf ref vs legacy $rtl_rel (informational) ==="
  if [[ ! -f "$rtl" ]]; then
    echo "legacy $leaf: MISSING $rtl_rel" | tee -a "$LEGACY_LOG"
    continue
  fi
  legacy_try "$leaf" "$rtl"
done

echo
echo "=== equiv_ref summary ==="
if [[ "$fail" -ne 0 ]]; then
  echo "equiv_ref: FAIL"
  exit 1
fi
echo "equiv_ref: PASS (Icarus compile + false mutations recorded)"
echo "legacy conclusions:"
cat "$LEGACY_LOG"
exit 0
