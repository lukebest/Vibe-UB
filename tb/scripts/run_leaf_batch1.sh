#!/usr/bin/env bash
# Leaf batch 1: rst_sync / rst_adapt / lane dist-dedist-collect / BCRC.
# Icarus 12.0 is the pass/fail gate (D7). Verilator is compare-only.
set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TB="$ROOT/tb"
SIM="${1:-icarus}"
SEED="${COCOTB_RANDOM_SEED:-1}"
export COCOTB_RANDOM_SEED="$SEED"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
if [[ -f "$ROOT/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/venv/bin/activate"
fi

mkdir -p "$TB/reports/regress/hooks0" "$TB/reports/regress/hooks1" \
         "$TB/reports/cov_func" "$TB/reports/regress"

PASS=0
FAIL=0
SKIP=0

run_one() {
  local leaf="$1" hooks="$2"
  shift 2
  local extra=("$@")
  local tag="${leaf}_h${hooks}"
  local nlanes="" pol=""
  local i
  for i in "${extra[@]+"${extra[@]}"}"; do
    case "$i" in
      NUM_LANES=*) nlanes="${i#NUM_LANES=}"; tag="${tag}_x${nlanes}" ;;
      PYC_RST_ACTIVE_HIGH=*) pol="${i#PYC_RST_ACTIVE_HIGH=}"; tag="${tag}_pol${pol}" ;;
    esac
  done
  local logdir="$TB/reports/regress/hooks${hooks}"
  local log="$logdir/${tag}.log"
  echo "=== $SIM $tag ==="
  rm -rf "$TB/sim_build"
  set +e
  make -C "$TB" leaf SIM="$SIM" LEAF="$leaf" TEST_HOOKS="$hooks" "${extra[@]}" \
    >"$log" 2>&1
  local rc=$?
  set -e
  if grep -qE '^FAIL ' "$log"; then
    echo "FAIL $tag (see $log)"
    grep -E '^(PASS|FAIL) ' "$log" | tail -n 20
    FAIL=$((FAIL + 1))
    return 0
  fi
  if [[ $rc -ne 0 ]]; then
    echo "FAIL $tag make_rc=$rc (see $log)"
    tail -n 40 "$log"
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

run_matrix() {
  local hooks
  for hooks in 0 1; do
    run_one ub_rst_sync "$hooks"
    run_one ub_pyc_rst_adapt "$hooks" PYC_RST_ACTIVE_HIGH=1
    run_one ub_pyc_rst_adapt "$hooks" PYC_RST_ACTIVE_HIGH=0
    local n
    for n in 1 2 4 8; do
      run_one ub_pcs_lane_dist "$hooks" NUM_LANES="$n"
      run_one ub_pcs_lane_dedist "$hooks" NUM_LANES="$n"
      run_one ub_pcs_lane_collect "$hooks" NUM_LANES="$n"
    done
    run_one ub_dll_bcrc "$hooks"
    run_one ub_dll_bcrc_check "$hooks"
  done
}

echo "SEED $SEED SIM $SIM"
run_matrix
python3 "$TB/scripts/summarize_tp.py" || true

echo "=== $SIM leaf-batch1 PASS=$PASS FAIL=$FAIL SKIP=$SKIP SEED=$SEED ==="
if [[ "$FAIL" -ne 0 ]]; then
  exit 1
fi
exit 0
