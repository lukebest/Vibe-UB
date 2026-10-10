#!/usr/bin/env bash
# One documented seq command. Do not use -set-init-def (Yosys 0.33 satgen.h:91).
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LEAF="${1:?leaf}"
NET="${2:?net}"
DEPTH="${3:-8}"
TMO="${4:-40}"
MODE="${5:-bmc}"   # bmc | induct | bmc0
LABEL="${6:-probe}"
OUT="/tmp/seq_probe_${LABEL}"
mkdir -p "$OUT"
INC=""
[[ -d "$ROOT/rtl/pyc_lib" ]] && INC="$INC -I$ROOT/rtl/pyc_lib"
[[ -d "$ROOT/rtl/common" ]] && INC="$INC -I$ROOT/rtl/common"
INC="$INC -I$(dirname "$NET")"
GOLD="$ROOT/formal/dll/ref/${LEAF}.sv"
GOLD_READ="read_verilog -sv $GOLD"
if [[ "$LEAF" == ub_dll_bcrc_check ]]; then
  GOLD_READ="read_verilog -sv $ROOT/formal/dll/ref/ub_dll_bcrc.sv; read_verilog -sv $GOLD"
fi
EXTRA=""
[[ "$MODE" == bmc0 ]] && EXTRA="-set in_data_in 0"
if [[ "$MODE" == induct ]]; then
  SAT="sat -verify -tempinduct -prove-asserts -prove-skip 2 -set-at 1 in_rst_pyc 1 -set-at 2 in_rst_pyc 1 -show-inputs -show-outputs -dump_vcd $OUT/cex.vcd -timeout $TMO"
else
  SAT="sat -seq $DEPTH -verify -prove-asserts -prove-skip 2 -set-at 1 in_rst_pyc 1 -set-at 2 in_rst_pyc 1 -show-inputs -show-outputs -show-regs $EXTRA -dump_vcd $OUT/cex.vcd -timeout $TMO"
fi
echo "SEQ_CMD leaf=$LEAF net=$NET mode=$MODE depth=$DEPTH tmo=$TMO"
echo "SEQ_SAT $SAT"
yosys -p "
$GOLD_READ
hierarchy -check -top $LEAF
rename -top gold
proc; flatten; opt_expr; opt_clean
design -stash gold
read_verilog -sv $INC $NET
hierarchy -check -top $LEAF
rename -top gate
proc; flatten; opt_expr; opt_clean
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
miter -equiv -flatten -make_assert gold gate miter
hierarchy -top miter
$SAT
" >"$OUT/yosys.log" 2>&1
echo "SEQ_RC=$?"
grep -E 'SAT proof|proof did|Time step|ERROR:|SUCCESS|FAIL!' "$OUT/yosys.log" | head -n 20
echo "SEQ_LOG=$OUT/yosys.log SEQ_VCD=$OUT/cex.vcd"
