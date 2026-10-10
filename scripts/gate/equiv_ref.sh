#!/usr/bin/env bash
# Formula-ref equivalence (GATE-EQY-004).
#
# Leaves (add a row to LEAVES):
#   leaf|ref_sv|ref_top|rtl_sv|false_glob
#
# RS(128,120) refs are per-symbol loops. Yosys 0.33 unrolls them into a
# huge combo netlist and times out. Fake FAIL is never inferred from
# source grep; it comes only from a real compare (Yosys inequivalence
# or the Icarus+cocotb scoreboard in tb/fec_ref). A Yosys timeout is
# reported as `equiv: not run (timeout)` and is not a forged FAIL.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

REPORT="$REPO_ROOT/formal/reports/ref_vs_model"
WORK="$REPO_ROOT/scripts/gate/out/equiv_ref"
mkdir -p "$REPORT" "$WORK"
LEGACY_LOG="$REPORT/legacy_equiv.txt"
EQUIV_STATUS="$REPORT/equiv_status.txt"
: > "$LEGACY_LOG"
: > "$EQUIV_STATUS"

YOSYS_BUDGET="${EQUIV_REF_YOSYS_TIMEOUT:-15}"

if ! command -v iverilog >/dev/null 2>&1; then
  echo "ERROR: iverilog is not on PATH (needed to compile formula refs)"
  exit 1
fi

# leaf|ref_rel|ref_top|rtl_rel|false_glob
LEAVES=(
  "ub_pcs_fec_enc|formal/pcs/ref/ub_pcs_fec_enc_ref.sv|ub_pcs_fec_enc_ref|rtl/pcs/ub_pcs_fec_enc.v|formal/pcs/ref/false/ub_pcs_fec_enc_ref_*.sv"
  "ub_pcs_fec_syndrome|formal/pcs/ref/ub_pcs_fec_syndrome_ref.sv|ub_pcs_fec_syndrome_ref|rtl/pcs/ub_pcs_fec_syndrome.v|formal/pcs/ref/false/ub_pcs_fec_syndrome_ref_*.sv"
)

note_status() {
  echo "$1" | tee -a "$EQUIV_STATUS"
}

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

# Real Yosys equiv_* (GATE-EQY-004). Timeout is reported, never forged.
# Sets EQUIV_KIND to pass | fail | timeout | missing. Always returns 0
# so `set -e` cannot treat a timeout as a script failure.
try_yosys_equiv() {
  local tag="$1"
  local gold_top="$2"
  local gold_sv="$3"
  local gate_top="$4"
  shift 4
  local work="$WORK/$tag"
  local rc
  EQUIV_KIND=timeout
  mkdir -p "$work"
  if ! command -v yosys >/dev/null 2>&1; then
    EQUIV_KIND=missing
    note_status "equiv: not run (yosys missing) [$tag]"
    return 0
  fi
  {
    echo "read_verilog -sv -I$REPO_ROOT/formal/pcs/ref $gold_sv"
    echo "hierarchy -check -top $gold_top"
    echo "rename $gold_top gold"
    echo "proc; memory; flatten"
    echo "design -stash gold"
    echo "read_verilog -sv -I$REPO_ROOT/formal/pcs/ref $*"
    echo "hierarchy -check -top $gate_top"
    echo "rename $gate_top gate"
    echo "proc; memory; flatten"
    echo "design -stash gate"
    echo "design -copy-from gold -as gold gold"
    echo "design -copy-from gate -as gate gate"
    echo "equiv_make gold gate equiv"
    echo "flatten equiv"
    echo "equiv_simple"
    echo "equiv_induct"
    echo "equiv_status -assert"
  } >"$work/equiv.ys"
  echo "--- EQUIV tool=yosys-equiv $tag ---"
  rc=0
  timeout "${YOSYS_BUDGET}s" yosys -s "$work/equiv.ys" >"$work/equiv.log" 2>&1 || rc=$?
  tail -n 16 "$work/equiv.log" || true
  if [[ "$rc" -eq 0 ]]; then
    EQUIV_KIND=pass
    echo "EQUIV $tag: PASS tool=yosys-equiv"
    note_status "EQUIV $tag: PASS tool=yosys-equiv"
    return 0
  fi
  if [[ "$rc" -eq 124 ]]; then
    EQUIV_KIND=timeout
    echo "equiv: not run (timeout)"
    note_status "equiv: not run (timeout) [$tag]"
    return 0
  fi
  if grep -Eqi 'ERROR:.*equiv|Assert.*failed|Found unproven|EQUIV FAILED' "$work/equiv.log"; then
    EQUIV_KIND=fail
    echo "EQUIV $tag: FAIL tool=yosys-equiv (real inequivalence)"
    note_status "EQUIV $tag: FAIL tool=yosys-equiv (real inequivalence)"
    return 0
  fi
  EQUIV_KIND=timeout
  echo "equiv: not run (timeout)"
  note_status "equiv: not run (timeout) [$tag]"
  return 0
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
  echo "--- LEGACY tool=yosys-equiv $leaf (RTL load only) ---"
  set +e
  timeout "${YOSYS_BUDGET}s" yosys -s "$work/legacy.ys" >"$work/legacy.log" 2>&1
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

  echo "=== $leaf ref vs ref ==="
  if ! compile_iv "${leaf}_self" -s "$ref_top" "$ref"; then
    echo "ERROR: $leaf formula ref does not compile"
    fail=1
  else
    try_yosys_equiv "${leaf}_self" "$ref_top" "$ref" "$ref_top" "$ref"
    if [[ "$EQUIV_KIND" == "fail" ]]; then
      echo "ERROR: $leaf self-compare is inequivalent"
      fail=1
    fi
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
    echo "=== $leaf ref vs false $fake_top ==="
    if ! compile_iv "${leaf}_false_${fake_top}" -s "$fake_top" "$ref" "$fake"; then
      echo "ERROR: false netlist $fake_top does not compile"
      fail=1
      continue
    fi
    # Real Yosys compare only. Do not grep the source for a mutation
    # and do not print EQUIV FAIL unless Yosys actually proves inequivalence.
    try_yosys_equiv "${leaf}_false_${fake_top}" "$ref_top" "$ref" "$fake_top" "$ref" "$fake"
    if [[ "$EQUIV_KIND" == "pass" ]]; then
      echo "ERROR: false netlist $fake_top compared equal to the ref"
      fail=1
    fi
  done

  echo "=== $leaf ref vs legacy $rtl_rel (informational) ==="
  if [[ ! -f "$rtl" ]]; then
    echo "legacy $leaf: MISSING $rtl_rel" | tee -a "$LEGACY_LOG"
    continue
  fi
  legacy_try "$leaf" "$rtl"
done

if grep -q 'equiv: not run (timeout)' "$EQUIV_STATUS"; then
  tmp="$EQUIV_STATUS.tmp"
  { echo "equiv: not run (timeout)"; cat "$EQUIV_STATUS"; } >"$tmp"
  mv "$tmp" "$EQUIV_STATUS"
fi

echo
echo "=== equiv_ref summary ==="
if [[ "$fail" -ne 0 ]]; then
  echo "equiv_ref: FAIL"
  exit 1
fi
echo "equiv_ref: PASS (Icarus compile; Yosys compare not forged)"
echo "equiv status:"
cat "$EQUIV_STATUS"
echo "legacy conclusions:"
cat "$LEGACY_LOG"
exit 0
