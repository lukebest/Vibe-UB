#!/usr/bin/env bash
# Emit ub_pcs_lane_dist via pyCircuit CLI + pycc, then lint / yosys / equiv.
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd -- "${HERE}/../.." && pwd)"
PYC_ROOT="${PYC_TOOLCHAIN_ROOT:-/tmp/spike/pyCircuit/.pycircuit_out/toolchain/install}"
VENV="${SPIKE_VENV:-/tmp/spike/venv}"
PYCC="${PYCC:-${PYC_ROOT}/bin/pycc}"
PYTHON="${VENV}/bin/python"
export PYC_TOOLCHAIN_ROOT="${PYC_ROOT}"
export PATH="${PYC_ROOT}/bin:${PATH}"

GEN="${HERE}/gen"
REF="${HERE}/ref"
PRIM="${PYC_ROOT}/include/verilog"
mkdir -p "${GEN}/n4" "${GEN}/n8" "${REF}"

emit_one() {
  local n="$1"
  local pyc="${GEN}/n${n}/ub_pcs_lane_dist.mlir"
  local v="${GEN}/n${n}/ub_pcs_lane_dist.v"
  echo "=== emit NUM_LANES=${n} ==="
  "${PYTHON}" -m pycircuit.cli emit "${HERE}/ub_pcs_lane_dist.py" \
    -o "${pyc}" \
    --project-root "${HERE}" \
    --param "num_lanes=${n}" \
    --param "pma_w=32" \
    --param "sym_w=8" \
    --param "test_hooks=0"
  # Combo leaf: no pyc_reg/fifo. `=0` turns off the default primitive includes.
  "${PYCC}" "${pyc}" --emit=verilog --include-primitives=0 -o "${v}"
  echo "wrote ${v}"
}

emit_one 4
emit_one 8

# Extract PR-branch reference (f-string emitter, parameterized).
git -C "${REPO}" show origin/cursor/rtl-m1-leaf-batch1-e5bb:rtl/pcs/ub_pcs_lane_dist.v \
  > "${REF}/ub_pcs_lane_dist_pr_e5bb.v"

echo "=== Verilator lint ==="
verilator --lint-only -Wall "${GEN}/n4/ub_pcs_lane_dist.v" 2>&1 | tee "${GEN}/verilator_n4.log"
verilator --lint-only -Wall "${GEN}/n8/ub_pcs_lane_dist.v" 2>&1 | tee "${GEN}/verilator_n8.log"
echo "verilator lint: OK"

yosys_stat() {
  local v="$1"
  local top="$2"
  local log="$3"
  yosys -p "
    read_verilog -sv ${v}
    hierarchy -check -top ${top}
    proc
    opt
    stat
    select -assert-none t:\$dlatch t:\$adff t:\$adffe t:\$dlatchsr
  " > "${log}" 2>&1
  rg -n "Number of cells|Number of wires|latch|ERROR|assert" "${log}" || true
  echo "yosys stat wrote ${log}"
}

echo "=== Yosys stat N=4 ==="
yosys_stat "${GEN}/n4/ub_pcs_lane_dist.v" ub_pcs_lane_dist "${GEN}/yosys_n4.log"
echo "=== Yosys stat N=8 ==="
yosys_stat "${GEN}/n8/ub_pcs_lane_dist.v" ub_pcs_lane_dist "${GEN}/yosys_n8.log"

yosys_equiv() {
  local gold_v="$1"
  local gold_top="$2"
  local gate_v="$3"
  local gate_top="$4"
  local chparam_cmd="$5"
  local log="$6"
  local label="$7"
  echo "=== Yosys equiv ${label} ==="
  set +e
  yosys -p "
    read_verilog -sv ${gold_v}
    ${chparam_cmd}
    hierarchy -check -top ${gold_top}
    flatten
    rename ${gold_top} gold
    design -stash gold

    read_verilog -sv ${gate_v}
    hierarchy -check -top ${gate_top}
    flatten
    rename ${gate_top} gate
    design -stash gate

    design -reset
    design -copy-from gold -as gold gold
    design -copy-from gate -as gate gate
    equiv_make gold gate equiv
    equiv_simple equiv
    equiv_induct equiv
    equiv_status -assert equiv
  " > "${log}" 2>&1
  local rc=$?
  set -e
  rg -n "ERROR|Assert|proved|unproven|equiv_status|FAILED" "${log}" || tail -20 "${log}"
  if [[ ${rc} -eq 0 ]]; then
    echo "equiv ${label}: PASS"
  else
    echo "equiv ${label}: FAIL (exit ${rc})"
  fi
  return 0
}

yosys_equiv \
  "${REF}/ub_pcs_lane_dist_pr_e5bb.v" ub_pcs_lane_dist \
  "${GEN}/n4/ub_pcs_lane_dist.v" ub_pcs_lane_dist \
  "chparam -set NUM_LANES 4 -set PMA_W 32 -set SYM_W 8 ub_pcs_lane_dist" \
  "${GEN}/equiv_n4_vs_pr.log" \
  "pycc-N4 vs PR e5bb"

yosys_equiv \
  "${REF}/ub_pcs_lane_dist_pr_e5bb.v" ub_pcs_lane_dist \
  "${GEN}/n8/ub_pcs_lane_dist.v" ub_pcs_lane_dist \
  "chparam -set NUM_LANES 8 -set PMA_W 32 -set SYM_W 8 ub_pcs_lane_dist" \
  "${GEN}/equiv_n8_vs_pr.log" \
  "pycc-N8 vs PR e5bb"

yosys_equiv \
  "${REF}/ub_pcs_lane_dist_spec.v" ub_pcs_lane_dist_spec \
  "${GEN}/n4/ub_pcs_lane_dist.v" ub_pcs_lane_dist \
  "chparam -set NUM_LANES 4 -set PMA_W 32 -set SYM_W 8 ub_pcs_lane_dist_spec" \
  "${GEN}/equiv_n4_vs_spec.log" \
  "pycc-N4 vs spec-gold"

yosys_equiv \
  "${REF}/ub_pcs_lane_dist_spec.v" ub_pcs_lane_dist_spec \
  "${GEN}/n8/ub_pcs_lane_dist.v" ub_pcs_lane_dist \
  "chparam -set NUM_LANES 8 -set PMA_W 32 -set SYM_W 8 ub_pcs_lane_dist_spec" \
  "${GEN}/equiv_n8_vs_spec.log" \
  "pycc-N8 vs spec-gold"

echo "=== Python model bit-exact ==="
"${PYTHON}" "${HERE}/check_model.py"
