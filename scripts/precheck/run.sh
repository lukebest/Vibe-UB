#!/usr/bin/env bash
# Non-gating local pre-check: Yosys equiv of pycc leaves vs scripts/precheck/
# SPEC-formula references. Official gate is formal/<layer>/ref/ (PR #16).
set -euo pipefail
REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO}"
export PYC_TOOLCHAIN_ROOT="${PYC_TOOLCHAIN_ROOT:-/tmp/pyCircuit/.pycircuit_out/toolchain/install}"
export PATH="${PYC_TOOLCHAIN_ROOT}/bin:${PATH}"
export UB_PYC_VENV="${UB_PYC_VENV:-/tmp/venv}"
EV="${EV:-/tmp/ub-ev}"
mkdir -p "${EV}"

equiv() {
  local gold="$1" gtop="$2" gate="$3" ttop="$4" extra="${5:-}" chg="${6:-}"
  local label="$7" to="${8:-90}"
  echo "==== PRECHECK (non-gating) $label ===="
  set +e
  timeout "${to}" yosys -q -p "
    read_verilog ${extra} -sv ${gold}
    ${chg}
    hierarchy -check -top ${gtop}
    proc; flatten; opt
    rename ${gtop} gold
    design -stash gold
    read_verilog ${extra} -sv ${gate}
    hierarchy -check -top ${ttop}
    proc; flatten; opt
    rename ${ttop} gate
    design -stash gate
    design -reset
    design -copy-from gold -as gold gold
    design -copy-from gate -as gate gate
    equiv_make gold gate equiv
    equiv_simple equiv
    equiv_induct equiv
    equiv_status -assert equiv
  " > "${EV}/${label}.log" 2>&1
  local rc=$?
  set -e
  if [[ ${rc} -eq 0 ]]; then
    echo "PASS ${label}"
  elif [[ ${rc} -eq 124 ]]; then
    echo "TIMEOUT ${label} (${to}s) — non-gating"
  else
    echo "FAIL ${label} rc=${rc} — non-gating; see ${EV}/${label}.log"
  fi
}

equiv scripts/precheck/ub_pyc_rst_adapt_spec.v ub_pyc_rst_adapt_spec \
      rtl/common/ub_pyc_rst_adapt.v ub_pyc_rst_adapt \
      "" "" rst_prod_vs_spec

equiv scripts/precheck/ub_pcs_lane_dist_spec.v ub_pcs_lane_dist_spec \
      rtl/pcs/ub_pcs_lane_dist_x4.v ub_pcs_lane_dist_x4 \
      "" "chparam -set NUM_LANES 4 ub_pcs_lane_dist_spec" lane_dist_x4_vs_spec
equiv scripts/precheck/ub_pcs_lane_dist_spec.v ub_pcs_lane_dist_spec \
      rtl/pcs/ub_pcs_lane_dist_x8.v ub_pcs_lane_dist_x8 \
      "" "chparam -set NUM_LANES 8 ub_pcs_lane_dist_spec" lane_dist_x8_vs_spec
equiv scripts/precheck/ub_pcs_lane_dedist_spec.v ub_pcs_lane_dedist_spec \
      rtl/pcs/ub_pcs_lane_dedist_x4.v ub_pcs_lane_dedist_x4 \
      "" "chparam -set NUM_LANES 4 ub_pcs_lane_dedist_spec" lane_dedist_x4_vs_spec
equiv scripts/precheck/ub_pcs_lane_dedist_spec.v ub_pcs_lane_dedist_spec \
      rtl/pcs/ub_pcs_lane_dedist_x8.v ub_pcs_lane_dedist_x8 \
      "" "chparam -set NUM_LANES 8 ub_pcs_lane_dedist_spec" lane_dedist_x8_vs_spec

# Combo next-state (the piece SAT can finish). Sequential full-chip BCRC
# equiv_induct vs bit-serial is recorded but not treated as a merge gate.
"${UB_PYC_VENV}/bin/python" scripts/precheck/emit_bcrc_next.py "${EV}/ub_dll_bcrc_next.v"
equiv scripts/precheck/ub_dll_bcrc_next_spec.v ub_dll_bcrc_next_spec \
      "${EV}/ub_dll_bcrc_next.v" ub_dll_bcrc_next \
      "-Irtl/common" "" bcrc_next_vs_spec 120

equiv scripts/precheck/ub_dll_bcrc_spec.v ub_dll_bcrc_spec \
      rtl/dll/ub_dll_bcrc.v ub_dll_bcrc \
      "-Irtl/common" "" bcrc_prod_vs_spec 90
equiv scripts/precheck/ub_dll_bcrc_check_spec.v ub_dll_bcrc_check_spec \
      rtl/dll/ub_dll_bcrc_check.v ub_dll_bcrc_check \
      "-Irtl/common" "" bcrc_check_prod_vs_spec 90

echo "precheck done (non-gating). logs in ${EV}/"
