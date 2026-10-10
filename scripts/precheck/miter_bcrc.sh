#!/usr/bin/env bash
# Local BCRC miter (non-gating). Gold = PR #16 formal ref (not committed here).
# Usage: miter_bcrc.sh gen|check <seq> [mode]
#   mode: bmc_rst | bmc_init0_rst | tempinduct
set -euo pipefail
KIND="${1:-gen}"
SEQ="${2:-8}"
MODE="${3:-bmc_rst}"
GOLD_ROOT="${GOLD_ROOT:-/tmp/pr16-gate}"
WS="$(cd "$(dirname "$0")/../.." && pwd)"
EV="${EV:-/tmp/ub-ev}"
mkdir -p "${EV}"

if [[ "${KIND}" == check ]]; then
  LEAF=ub_dll_bcrc_check
  GOLD_READ="read_verilog -sv ${GOLD_ROOT}/formal/dll/ref/ub_dll_bcrc.sv ${GOLD_ROOT}/formal/dll/ref/ub_dll_bcrc_check.sv"
  GATE="${WS}/rtl/dll/ub_dll_bcrc_check.v"
else
  LEAF=ub_dll_bcrc
  GOLD_READ="read_verilog -sv ${GOLD_ROOT}/formal/dll/ref/ub_dll_bcrc.sv"
  GATE="${WS}/rtl/dll/ub_dll_bcrc.v"
fi

case "${MODE}" in
  bmc_rst)
    SAT="sat -verify -prove trigger 0 -seq ${SEQ} -set-at 1 in_rst_pyc 1 -show-ports -dump_vcd ${EV}/${LEAF}_${MODE}.vcd"
    ;;
  bmc_init0_rst)
    SAT="sat -verify -prove trigger 0 -set-init-zero -seq ${SEQ} -set-at 1 in_rst_pyc 1 -show-ports -dump_vcd ${EV}/${LEAF}_${MODE}.vcd"
    ;;
  tempinduct)
    SAT="sat -verify -tempinduct -prove trigger 0 -set-init-zero -seq ${SEQ} -set-at 1 in_rst_pyc 1 -show-ports -dump_vcd ${EV}/${LEAF}_${MODE}.vcd"
    ;;
  *)
    echo "unknown mode ${MODE}" >&2
    exit 2
    ;;
esac

SCRIPT="
${GOLD_READ}
hierarchy -check -top ${LEAF}
rename -top gold
proc; flatten; opt
design -stash gold

read_verilog -sv -I${WS}/rtl/pyc_lib ${GATE}
hierarchy -check -top ${LEAF}
rename -top gate
proc; flatten; opt
design -stash gate

design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
miter -equiv -flatten -make_outputs -ignore_gold_x gold gate miter
hierarchy -top miter
${SAT}
"

echo "==== miter ${LEAF} ${MODE} seq=${SEQ} ===="
set +e
timeout 180 yosys -p "${SCRIPT}" > "${EV}/${LEAF}_${MODE}.log" 2>&1
RC=$?
set -e
if [[ ${RC} -eq 0 ]]; then
  echo "PROVE ${LEAF} ${MODE} seq=${SEQ}"
elif [[ ${RC} -eq 124 ]]; then
  echo "TIMEOUT ${LEAF} ${MODE} seq=${SEQ}"
else
  echo "CEX_OR_FAIL ${LEAF} ${MODE} seq=${SEQ} rc=${RC}"
fi
rg -n "SAT|FAIL|prove|trigger|Counter|Assert|ERROR|satisfiable|unique-sat" "${EV}/${LEAF}_${MODE}.log" | head -40
echo "log ${EV}/${LEAF}_${MODE}.log"
