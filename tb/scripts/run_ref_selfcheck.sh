#!/usr/bin/env bash
# Cocotb: formula refs vs model/tb.models. No product netlist required.
# Xia: on bit mismatch, do not edit formal/ref or the model; see formal/reports/.
set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TB="$ROOT/tb"
SIM="${1:-icarus}"
SEED="${COCOTB_RANDOM_SEED:-1}"
export COCOTB_RANDOM_SEED="$SEED"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export REF=1
if [[ -f "$ROOT/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/venv/bin/activate"
fi

PASS=0
FAIL=0

run_one() {
  local leaf="$1"
  shift
  local extra=("$@")
  local tag="${leaf}"
  local i
  for i in "${extra[@]+"${extra[@]}"}"; do
    case "$i" in
      NUM_LANES=*) tag="${tag}_x${i#NUM_LANES=}" ;;
      PYC_RST_ACTIVE_HIGH=*) tag="${tag}_pol${i#PYC_RST_ACTIVE_HIGH=}" ;;
    esac
  done
  local logdir="$TB/reports/regress/$SIM/ref"
  mkdir -p "$logdir"
  local log="$logdir/${tag}.log"
  echo "=== REF $SIM $tag ==="
  rm -rf "$TB/sim_build"
  set +e
  make -C "$TB" leaf SIM="$SIM" LEAF="$leaf" REF=1 TEST_HOOKS=0 \
    ${extra[@]+"${extra[@]}"} >"$log" 2>&1
  local rc=$?
  set -e
  grep -E '^DUT_RTL=' "$log" | head -n 1 || true
  grep -E '^SCOREBOARD |^PASS .*_suite|^FAIL ' "$log" | tail -n 8 || true
  if grep -qE '^FAIL ' "$log" || [[ $rc -ne 0 ]]; then
    echo "FAIL $tag (see $log)"
    FAIL=$((FAIL + 1))
    return 0
  fi
  if grep -qE '^PASS ' "$log"; then
    echo "PASS $tag"
    PASS=$((PASS + 1))
  else
    echo "FAIL $tag no PASS line"
    FAIL=$((FAIL + 1))
  fi
}

echo "SEED $SEED SIM $SIM REF=1"
run_one ub_pyc_rst_adapt PYC_RST_ACTIVE_HIGH=1
run_one ub_pyc_rst_adapt PYC_RST_ACTIVE_HIGH=0
for n in 1 2 4 8; do
  run_one ub_pcs_lane_dist NUM_LANES="$n"
  run_one ub_pcs_lane_dedist NUM_LANES="$n"
  run_one ub_pcs_lane_collect NUM_LANES="$n"
done
run_one ub_dll_bcrc
run_one ub_dll_bcrc_check

echo "=== $SIM ref-selfcheck PASS=$PASS FAIL=$FAIL SEED=$SEED ==="
if [[ "$FAIL" -ne 0 ]]; then
  echo "Xia: mismatches (if any) are under formal/reports/ref_vs_model/ — do not edit ref or model."
  exit 1
fi
exit 0
