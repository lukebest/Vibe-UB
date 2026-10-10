#!/usr/bin/env bash
# Compare a caller-supplied netlist to the verification formula reference.
# Usage: equiv_ref.sh <leaf> <netlist.v>
# Does not read rtl/ and does not require a design PR.
# Gold = formal/<layer>/ref/<leaf>.sv
# Exit 0 only if every output is proven (equiv_* or miter tempinduct)
# or, for BCRC, the affine next-state basis matches in every control cube.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LEAF="${1:-}"
NET="${2:-}"
# Per-method SAT / yosys wall time. Tempinduct on a 160-bit CRC XOR is heavy.
EQUIV_TMO="${EQUIV_TMO:-90}"

usage() {
  echo "usage: $0 <leaf> <netlist.v>" >&2
  echo "  leaf: ub_pcs_lane_dist|ub_pcs_lane_dedist|ub_pcs_lane_collect" >&2
  echo "        ub_dll_bcrc|ub_dll_bcrc_check|ub_pyc_rst_adapt" >&2
  echo "  Gold is always chparam'd. Gate is chparam'd only if it declares the" >&2
  echo "  Verilog parameter (old / handwritten). pycc §2.2 nets have no params;" >&2
  echo "  polarity / NUM_LANES are taken from the variant tag or env." >&2
  echo "  EQUIV_INC=dir[:dir] extra include dirs for gate \`include (pyc_reg.v)." >&2
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

has_param() {
  # Leaf-level parameter only (not pyc_reg #(.WIDTH)).
  local file="$1" name="$2"
  grep -qE "parameter[[:space:]]+(integer[[:space:]]+)?${name}[[:space:]]*[=,)]" "$file" \
    || grep -qE "parameter[[:space:]]+(integer[[:space:]]+)?${name}[[:space:]]*$" "$file"
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

NET_ABS="$(cd "$(dirname "$NET")" && pwd)/$(basename "$NET")"
NET_BASE="$(basename "$NET" .v)"
NET_BASE="${NET_BASE%.sv}"

GATE_TOP="$(
  tr -d '\r' <"$NET_ABS" | sed -n 's/^[[:space:]]*module[[:space:]]\+\([A-Za-z_][A-Za-z0-9_]*\).*/\1/p' | head -n 1
)"
[[ -n "$GATE_TOP" ]] || { echo "equiv_ref: no module in $NET" >&2; exit 2; }

NUM_LANES="${NUM_LANES:-}"
if [[ -z "$NUM_LANES" ]]; then
  if [[ "$NET_BASE" =~ _x([0-9]+)$ ]]; then
    NUM_LANES="${BASH_REMATCH[1]}"
  elif [[ "$GATE_TOP" =~ _x([0-9]+)$ ]]; then
    NUM_LANES="${BASH_REMATCH[1]}"
  elif [[ "$LEAF" == ub_pcs_lane_* ]]; then
    NUM_LANES=4
  fi
fi

if [[ -z "${PYC_RST_ACTIVE_HIGH+x}" || -z "${PYC_RST_ACTIVE_HIGH}" ]]; then
  PYC_RST_ACTIVE_HIGH=1
  case "$NET_BASE$GATE_TOP" in
    *_pol0*|*_active_low*|*_al) PYC_RST_ACTIVE_HIGH=0 ;;
    *_pol1*|*_active_high*|*_ah) PYC_RST_ACTIVE_HIGH=1 ;;
  esac
fi

gold_ch=""
gate_ch=""
if [[ "$LEAF" == ub_pcs_lane_* ]]; then
  if has_param "$GOLD" NUM_LANES; then
    gold_ch="chparam -set NUM_LANES ${NUM_LANES} ${LEAF}"
  fi
  if has_param "$NET_ABS" NUM_LANES; then
    gate_ch="chparam -set NUM_LANES ${NUM_LANES} ${GATE_TOP}"
  fi
fi
if [[ "$LEAF" == ub_pyc_rst_adapt ]]; then
  if has_param "$GOLD" PYC_RST_ACTIVE_HIGH; then
    gold_ch="chparam -set PYC_RST_ACTIVE_HIGH ${PYC_RST_ACTIVE_HIGH} ${LEAF}"
  fi
  if has_param "$NET_ABS" PYC_RST_ACTIVE_HIGH; then
    gate_ch="chparam -set PYC_RST_ACTIVE_HIGH ${PYC_RST_ACTIVE_HIGH} ${GATE_TOP}"
  fi
fi

INC_FLAGS=()
add_inc() {
  local d="$1"
  [[ -d "$d" ]] || return 0
  local abs
  abs="$(cd "$d" && pwd)"
  local x
  for x in "${INC_FLAGS[@]+"${INC_FLAGS[@]}"}"; do
    [[ "$x" == "$abs" ]] && return 0
  done
  INC_FLAGS+=("$abs")
}
add_inc "$(dirname "$NET_ABS")"
add_inc "$(dirname "$NET_ABS")/../common"
if [[ -n "${EQUIV_INC:-}" ]]; then
  IFS=':' read -r -a _incs <<<"$EQUIV_INC"
  for local_i in "${_incs[@]}"; do
    add_inc "$local_i"
  done
fi

gold_read=""
for f in "${GOLD_FILES[@]}"; do
  gold_read+="read_verilog -sv ${f}; "
done
gate_read="read_verilog -sv"
for d in "${INC_FLAGS[@]+"${INC_FLAGS[@]}"}"; do
  gate_read+=" -I${d}"
done
gate_read+=" ${NET_ABS}; "

prep_gold="
${gold_read}
${gold_ch}
hierarchy -check -top ${LEAF}
rename -top gold
proc; flatten; opt_expr; opt_clean
design -stash gold
"
prep_gate="
${gate_read}
${gate_ch}
hierarchy -check -top ${GATE_TOP}
rename -top gate
proc; flatten; opt_expr; opt_clean
design -stash gate
"
restore="
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
"

run_yosys() {
  local script="$1"
  local tmo="${2:-0}"
  set +e
  if [[ "$tmo" -gt 0 ]] && command -v timeout >/dev/null 2>&1; then
    OUT="$(timeout "$tmo" yosys -q -p "$script" 2>&1)"
    RC=$?
  else
    OUT="$(yosys -q -p "$script" 2>&1)"
    RC=$?
  fi
  set -e
  if [[ -n "${OUT:-}" ]]; then
    echo "$OUT"
  fi
  return "$RC"
}

pass_method() {
  METHOD="$1"
  echo "equiv_ref METHOD=${METHOD}"
  echo "equiv_ref PASS ${LEAF} vs $(basename "$NET")"
  exit 0
}

METHOD=""
echo "equiv_ref leaf=${LEAF} gold=${GOLD} gate=${NET_ABS} top=${GATE_TOP} NUM_LANES=${NUM_LANES:-n/a} PYC=${PYC_RST_ACTIVE_HIGH} gate_chparam=${gate_ch:-none}"

# 1) default equiv_make / simple / induct
SCRIPT1="${prep_gold}${prep_gate}${restore}
equiv_make gold gate equiv
equiv_simple equiv
equiv_induct equiv
equiv_status -assert equiv
"
if run_yosys "$SCRIPT1"; then
  pass_method "equiv_make+simple+induct"
fi
echo "equiv_ref note: default equiv_* left unproven cells; trying -seq/-undef/equiv_struct"

# 2) deeper equiv_simple + struct (combo-depth / window)
SCRIPT2="${prep_gold}${prep_gate}${restore}
equiv_make gold gate equiv
equiv_simple -seq 8 -undef equiv
equiv_struct equiv
equiv_simple -seq 8 equiv
equiv_induct equiv
equiv_status -assert equiv
"
if run_yosys "$SCRIPT2" "$EQUIV_TMO"; then
  pass_method "equiv_simple -seq 8 -undef + equiv_struct + induct"
fi
echo "equiv_ref note: still unproven; trying miter -equiv + sat -tempinduct"

# 3) miter + temporal induction (unbounded). Must prove all asserts.
SCRIPT3="${prep_gold}${prep_gate}${restore}
miter -equiv -flatten -make_assert gold gate miter
hierarchy -top miter
sat -verify -tempinduct -prove-asserts -set-init-zero -timeout $EQUIV_TMO
"
if run_yosys "$SCRIPT3" "$((EQUIV_TMO + 15))"; then
  pass_method "miter -equiv -flatten -make_assert + sat -tempinduct -prove-asserts -set-init-zero"
fi
echo "equiv_ref note: output-only tempinduct did not finish; pairing hidden CRC and retrying"

# 4) pair remainder (crc_gold / crc_q_gate) then tempinduct. BMC-only is not a PASS.
SCRIPT4="${prep_gold}${prep_gate}${restore}
equiv_make gold gate equiv
cd equiv
equiv_add -try crc_gold crc_q_gate
equiv_add -try crc_gold pyc_reg_9_gate
equiv_add -try crc_gold pyc_reg_15_gate
equiv_miter -assert miter
cd miter
sat -verify -tempinduct -prove-asserts -set-init-zero -timeout $EQUIV_TMO
"
if run_yosys "$SCRIPT4" "$((EQUIV_TMO + 15))"; then
  pass_method "equiv_add crc + miter -assert + sat -tempinduct -prove-asserts -set-init-zero"
fi

# 5) BCRC: affine next-state basis (complete for the remainder map).
# Handwritten fakes have no pyc_reg / crc_q; they already failed tempinduct.
if [[ "$LEAF" == ub_dll_bcrc || "$LEAF" == ub_dll_bcrc_check ]] \
   && grep -qE 'pyc_reg|crc_q__next' "$NET_ABS"; then
  echo "equiv_ref note: SAT timed out on the 190-input XOR; running next-state basis"
  INC_ARGS=()
  for d in "${INC_FLAGS[@]+"${INC_FLAGS[@]}"}"; do
    INC_ARGS+=(--inc "$d")
  done
  set +e
  python3 "$ROOT/scripts/gate/equiv_seq_basis.py" "$LEAF" "$GOLD" "$NET_ABS" "$GATE_TOP" \
    "${INC_ARGS[@]+"${INC_ARGS[@]}"}"
  RC=$?
  set -e
  if [[ "$RC" -eq 0 ]]; then
    pass_method "next-state affine basis (crc/data unit vectors × control cubes)"
  fi
fi

echo "equiv_ref METHOD=unproven" >&2
echo "equiv_ref FAIL ${LEAF} vs $(basename "$NET")" >&2
exit 1
