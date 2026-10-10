#!/usr/bin/env bash
# Compare a caller-supplied netlist to the verification formula reference.
# Usage: equiv_ref.sh <leaf> <netlist.v>
# Does not read rtl/ and does not require a design PR.
# Gold = formal/<layer>/ref/<leaf>.sv
# Yosys equiv_make / equiv_simple / equiv_induct / equiv_status -assert
# Exit 0 only if every output is proven.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LEAF="${1:-}"
NET="${2:-}"

usage() {
  echo "usage: $0 <leaf> <netlist.v>" >&2
  echo "  leaf: ub_pcs_lane_dist|ub_pcs_lane_dedist|ub_pcs_lane_collect" >&2
  echo "        ub_dll_bcrc|ub_dll_bcrc_check|ub_pyc_rst_adapt" >&2
  echo "  NUM_LANES / PYC_RST_ACTIVE_HIGH: optional env; _xN in the netlist name is used if set" >&2
  exit 2
}

[[ -n "$LEAF" && -n "$NET" ]] || usage
[[ -f "$NET" ]] || { echo "equiv_ref: netlist not found: $NET" >&2; exit 2; }

layer_of() {
  case "$1" in
    ub_pcs_lane_dist|ub_pcs_lane_dedist|ub_pcs_lane_collect) echo pcs ;;
    ub_dll_bcrc|ub_dll_bcrc_check) echo dll ;;
    ub_pyc_rst_adapt) echo common ;;
    *) echo "" ;;
  esac
}

LAYER="$(layer_of "$LEAF")"
[[ -n "$LAYER" ]] || { echo "equiv_ref: unknown leaf $LEAF" >&2; exit 2; }

GOLD="$ROOT/formal/$LAYER/ref/$LEAF.sv"
[[ -f "$GOLD" ]] || { echo "equiv_ref: missing reference $GOLD" >&2; exit 2; }

if ! command -v yosys >/dev/null 2>&1; then
  echo "equiv_ref: yosys not on PATH" >&2
  exit 2
fi

GOLD_FILES=("$GOLD")
case "$LEAF" in
  ub_pcs_lane_collect)
    GOLD_FILES=(
      "$ROOT/formal/pcs/ref/ub_pcs_lane_dist.sv"
      "$ROOT/formal/pcs/ref/ub_pcs_lane_dedist.sv"
      "$GOLD"
    )
    ;;
  ub_dll_bcrc_check)
    GOLD_FILES=(
      "$ROOT/formal/dll/ref/ub_dll_bcrc.sv"
      "$GOLD"
    )
    ;;
esac

NET_BASE="$(basename "$NET" .v)"
NET_BASE="${NET_BASE%.sv}"
NUM_LANES="${NUM_LANES:-}"
if [[ -z "$NUM_LANES" && "$NET_BASE" =~ _x([0-9]+)$ ]]; then
  NUM_LANES="${BASH_REMATCH[1]}"
fi
if [[ -z "$NUM_LANES" && "$LEAF" == ub_pcs_lane_* ]]; then
  NUM_LANES=4
fi
PYC_RST_ACTIVE_HIGH="${PYC_RST_ACTIVE_HIGH:-1}"

GATE_TOP="$(
  tr -d '\r' <"$NET" | sed -n 's/^[[:space:]]*module[[:space:]]\+\([A-Za-z_][A-Za-z0-9_]*\).*/\1/p' | head -n 1
)"
[[ -n "$GATE_TOP" ]] || { echo "equiv_ref: no module in $NET" >&2; exit 2; }

gold_ch=""
gate_ch=""
if [[ "$LEAF" == ub_pcs_lane_* ]]; then
  gold_ch="chparam -set NUM_LANES ${NUM_LANES} ${LEAF}"
  if [[ "$GATE_TOP" == "$LEAF" ]]; then
    gate_ch="chparam -set NUM_LANES ${NUM_LANES} ${GATE_TOP}"
  fi
fi
if [[ "$LEAF" == ub_pyc_rst_adapt ]]; then
  gold_ch="chparam -set PYC_RST_ACTIVE_HIGH ${PYC_RST_ACTIVE_HIGH} ${LEAF}"
  if [[ "$GATE_TOP" == "$LEAF" ]]; then
    gate_ch="chparam -set PYC_RST_ACTIVE_HIGH ${PYC_RST_ACTIVE_HIGH} ${GATE_TOP}"
  fi
fi

gold_read=""
for f in "${GOLD_FILES[@]}"; do
  gold_read+="read_verilog -sv ${f}; "
done
gate_read="read_verilog -sv ${NET}; "

# Stash gold, then gate. A second read_verilog would drop the renamed gold.
SCRIPT="
${gold_read}
${gold_ch}
hierarchy -check -top ${LEAF}
rename -top gold
proc; flatten; opt
design -stash gold

${gate_read}
${gate_ch}
hierarchy -check -top ${GATE_TOP}
rename -top gate
proc; flatten; opt
design -stash gate

design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
equiv_simple equiv
equiv_induct equiv
equiv_status -assert equiv
"

echo "equiv_ref leaf=${LEAF} gold=${GOLD} gate=${NET} top=${GATE_TOP} NUM_LANES=${NUM_LANES:-n/a} PYC=${PYC_RST_ACTIVE_HIGH}"
set +e
OUT="$(yosys -q -p "$SCRIPT" 2>&1)"
RC=$?
set -e
if [[ -n "$OUT" ]]; then
  echo "$OUT"
fi
if [[ "$RC" -eq 0 ]]; then
  echo "equiv_ref PASS ${LEAF} vs $(basename "$NET")"
  exit 0
fi
echo "equiv_ref FAIL ${LEAF} vs $(basename "$NET") rc=${RC}" >&2
exit 1
