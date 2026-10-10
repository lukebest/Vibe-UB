#!/usr/bin/env bash
# Compare a caller-supplied netlist to the verification formula reference.
# Usage: equiv_ref.sh <leaf> <netlist.v>
# Does not read rtl/ and does not require a design PR.
# Gold = formal/<layer>/ref/<leaf>.sv
# Exit 0 only if a recognized method proves the compare (timeout = unproven):
#   (1) equiv_make / equiv_simple / equiv_induct
#   (2) miter + sat -tempinduct
#   (3) miter + ABC dsec (or &cec after FFs are ports)
#   (4) register pairing by normalized Q name + name-paired miter + reset check
# Affine next-state basis is not a recognized pass (premise unproven).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LEAF="${1:-}"
NET="${2:-}"
# Per-method wall time. Timeout of a method is unproven; try the next.
EQUIV_TMO="${EQUIV_TMO:-90}"
# Comma list: equiv,sat,abc,regpair,seq  (default first four, in that order)
EQUIV_METHODS="${EQUIV_METHODS:-equiv,sat,abc,regpair}"
# abc family: dsec, cec, both (default). cec skips sequential dsec.
EQUIV_ABC_STAGE="${EQUIV_ABC_STAGE:-both}"
# Uncut output-only BMC / tempinduct depth (seq method).
EQUIV_SEQ_DEPTH="${EQUIV_SEQ_DEPTH:-16}"

usage() {
  echo "usage: $0 <leaf> <netlist.v>" >&2
  echo "  leaf: ub_pcs_lane_dist|ub_pcs_lane_dedist|ub_pcs_lane_collect" >&2
  echo "        ub_dll_bcrc|ub_dll_bcrc_check|ub_pyc_rst_adapt" >&2
  echo "  Gold is always chparam'd. Gate is chparam'd only if it declares the" >&2
  echo "  Verilog parameter (old / handwritten). pycc §2.2 nets have no params;" >&2
  echo "  polarity / NUM_LANES are taken from the variant tag or env." >&2
  echo "  Always -I rtl/pyc_lib for pycc \`include \"pyc_reg.v\". If that dir is" >&2
  echo "  missing (main before #5/#21), fall back to -I rtl/common and WARN." >&2
  echo "  EQUIV_INC=dir[:dir] extra include dirs (after the repo primitive dir)." >&2
  echo "  EQUIV_METHODS=equiv,sat,abc,regpair,seq  families to try (default first four)." >&2
  echo "  EQUIV_ABC_STAGE=dsec|cec|both  (default both)." >&2
  echo "  EQUIV_SEQ_DEPTH=N  uncut output-only BMC/tempinduct (default 16)." >&2
  echo "  EQUIV_TMO=seconds per method (default 90). Timeout = unproven." >&2
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
# SPEC §2.2: one copy of pyc_reg.v (and other pyc_* primitives) in rtl/pyc_lib/.
# main may not have that directory yet — same fallback as scripts/impl/quick_synth.py.
PYC_INC="none"
if [[ -d "$ROOT/rtl/pyc_lib" ]]; then
  add_inc "$ROOT/rtl/pyc_lib"
  PYC_INC="rtl/pyc_lib"
elif [[ -d "$ROOT/rtl/common" ]]; then
  add_inc "$ROOT/rtl/common"
  PYC_INC="rtl/common"
  echo "WARN: rtl/pyc_lib/ missing; falling back to rtl/common for Yosys -I" >&2
else
  echo "WARN: neither rtl/pyc_lib nor rtl/common exists; \`include may fail" >&2
fi
add_inc "$(dirname "$NET_ABS")"
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
# Check gold instantiates ub_dll_bcrc. A standalone pycc check net does not.
if [[ "$LEAF" == ub_dll_bcrc_check ]] \
   && ! grep -qE '^[[:space:]]*module[[:space:]]+ub_dll_bcrc[[:space:]]*[(#]' "$NET_ABS"; then
  gate_read="read_verilog -sv ${ROOT}/formal/dll/ref/ub_dll_bcrc.sv; ${gate_read}"
fi

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

has_method() {
  [[ ",${EQUIV_METHODS}," == *",$1,"* ]]
}

sec_now() { date +%s; }

log_time() {
  local name="$1" t0="$2" result="$3"
  local t1
  t1="$(sec_now)"
  echo "equiv_ref TIME method=${name} sec=$((t1 - t0)) result=${result}"
}

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

# Real compare FAIL (SAT CEX / proven nonequiv). Do not treat as "unproven".
fail_if_cex() {
  local method="$1"
  local out="$2"
  local line
  if printf '%s\n' "$out" | grep -qiE 'time ?out|timed out'; then
    return 0
  fi
  line="$(printf '%s\n' "$out" | grep -iE 'Assert failed|SAT proof finished - model found|SAT Model|NOT EQUIVALENT|Verification failed|proof did fail|was asserted|ERROR:.*[Nn]ot equivalent' | head -n 1 || true)"
  if printf '%s\n' "$out" | grep -qiE 'Assert failed|SAT proof finished - model found|SAT Model found|NOT EQUIVALENT|Verification failed|proof did fail|was asserted'; then
    echo "equiv_ref METHOD=${method}"
    echo "equiv_ref FAIL ${LEAF} vs $(basename "$NET") (${method}: ${line:-counterexample})"
    exit 1
  fi
}

abc_parse() {
  local log="$1"
  if grep -qE 'Networks are equivalent' "$log"; then
    echo equivalent
  elif grep -qiE 'NOT EQUIVALENT|Verification failed|was asserted|SATISFIABLE' "$log"; then
    echo not_equivalent
  else
    echo unproven
  fi
}

# (3) write_aiger gold/gate then yosys-abc dsec; combo nets fall through to cec.
# If dsec cannot run, miter -make_outputs + &r; &cec -m (FFs already in the AIG).
try_abc() {
  local t0 tmp abc_bin tmo log rc kind
  t0="$(sec_now)"
  abc_bin="$(command -v yosys-abc || true)"
  if [[ -z "$abc_bin" ]]; then
    echo "equiv_ref note: yosys-abc not on PATH; ABC method unproven"
    log_time "abc-dsec" "$t0" "unproven"
    return 1
  fi
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/equiv_ref_abc.XXXXXX")"
  tmo="$EQUIV_TMO"
  echo "equiv_ref note: trying miter/write_aiger + ABC dsec|&cec (yosys-abc) stage=${EQUIV_ABC_STAGE}"

  local script_aig="${prep_gold}${prep_gate}
design -load gold
hierarchy -top gold
techmap; opt; dffunmap; aigmap; opt
write_aiger -symbols ${tmp}/gold.aig
design -load gate
hierarchy -top gate
techmap; opt; dffunmap; aigmap; opt
write_aiger -symbols ${tmp}/gate.aig
"
  set +e
  if ! run_yosys "$script_aig" "$tmo"; then
    set -e
    echo "equiv_ref note: AIGER write failed or timed out"
    log_time "abc-dsec" "$t0" "timeout"
    rm -rf "$tmp"
    return 1
  fi
  set -e
  if [[ ! -s "${tmp}/gold.aig" || ! -s "${tmp}/gate.aig" ]]; then
    echo "equiv_ref note: empty AIGER"
    log_time "abc-dsec" "$t0" "unproven"
    rm -rf "$tmp"
    return 1
  fi

  if [[ "$EQUIV_ABC_STAGE" != "cec" ]]; then
    log="${tmp}/dsec.log"
    set +e
    timeout "$tmo" "$abc_bin" -c "dsec -T ${tmo} -v ${tmp}/gold.aig ${tmp}/gate.aig" \
      >"$log" 2>&1
    rc=$?
    set -e
    cat "$log"
    if grep -q 'has no latches' "$log"; then
      echo "equiv_ref note: no latches; running combinational cec"
      log="${tmp}/cec_combo.log"
      set +e
      timeout "$tmo" "$abc_bin" -c "cec -T ${tmo} -v ${tmp}/gold.aig ${tmp}/gate.aig" \
        >"$log" 2>&1
      rc=$?
      set -e
      cat "$log"
    fi
    kind="$(abc_parse "$log")"
    if [[ "$kind" == equivalent ]]; then
      log_time "abc-dsec" "$t0" "equivalent"
      rm -rf "$tmp"
      pass_method "miter + write_aiger + ABC dsec (yosys-abc)"
    fi
    if [[ "$kind" == not_equivalent ]]; then
      log_time "abc-dsec" "$t0" "not_equivalent"
      rm -rf "$tmp"
      echo "equiv_ref METHOD=abc-dsec" >&2
      echo "equiv_ref FAIL ${LEAF} vs $(basename "$NET") (ABC dsec: not equivalent)" >&2
      exit 1
    fi
    if [[ "$rc" -eq 124 ]]; then
      echo "equiv_ref note: ABC dsec timed out"
      log_time "abc-dsec" "$t0" "timeout"
    else
      log_time "abc-dsec" "$t0" "unproven"
    fi
  fi

  if [[ "$EQUIV_ABC_STAGE" == "dsec" ]]; then
    rm -rf "$tmp"
    return 1
  fi

  # Fallback: single-output miter AIGER + &cec -m (combo, or FFs already ports).
  echo "equiv_ref note: dsec unproven; trying miter -make_outputs + &cec -m"
  local script_m="${prep_gold}${prep_gate}${restore}
miter -equiv -flatten -make_outputs gold gate miter
hierarchy -top miter
techmap; opt; dffunmap; aigmap; opt
write_aiger -symbols -miter ${tmp}/miter.aig
"
  t0="$(sec_now)"
  set +e
  if ! run_yosys "$script_m" "$tmo"; then
    set -e
    log_time "abc-cec" "$t0" "timeout"
    rm -rf "$tmp"
    return 1
  fi
  set -e
  log="${tmp}/cec.log"
  set +e
  timeout "$tmo" "$abc_bin" -c "&r ${tmp}/miter.aig; &cec -m -v -T ${tmo}" \
    >"$log" 2>&1
  rc=$?
  set -e
  cat "$log"
  kind="$(abc_parse "$log")"
  if [[ "$kind" == equivalent ]]; then
    log_time "abc-cec" "$t0" "equivalent"
    rm -rf "$tmp"
    pass_method "miter -equiv -flatten -make_outputs + ABC &cec (yosys-abc)"
  fi
  if [[ "$kind" == not_equivalent ]]; then
    log_time "abc-cec" "$t0" "not_equivalent"
    rm -rf "$tmp"
    echo "equiv_ref METHOD=abc-cec" >&2
    echo "equiv_ref FAIL ${LEAF} vs $(basename "$NET") (ABC &cec: not equivalent)" >&2
    exit 1
  fi
  if [[ "$rc" -eq 124 ]]; then
    log_time "abc-cec" "$t0" "timeout"
  else
    log_time "abc-cec" "$t0" "unproven"
  fi
  rm -rf "$tmp"
  return 1
}

pass_method() {
  METHOD="$1"
  echo "equiv_ref METHOD=${METHOD}"
  echo "equiv_ref PASS ${LEAF} vs $(basename "$NET")"
  exit 0
}

METHOD=""
ABC_BIN="$(command -v yosys-abc || echo MISSING)"
YOSYS_VER="$(yosys -V 2>/dev/null | head -n 1)"
YOSYS_PKG="$(dpkg-query -W -f='${Version}' yosys 2>/dev/null || echo unknown)"
echo "equiv_ref abc=${ABC_BIN} yosys=${YOSYS_VER} yosys_pkg=${YOSYS_PKG}"
echo "equiv_ref leaf=${LEAF} gold=${GOLD} gate=${NET_ABS} top=${GATE_TOP} NUM_LANES=${NUM_LANES:-n/a} PYC=${PYC_RST_ACTIVE_HIGH} gate_chparam=${gate_ch:-none} pyc_inc=${PYC_INC} methods=${EQUIV_METHODS}"

# 1) equiv_*
if has_method equiv; then
  t0="$(sec_now)"
  SCRIPT1="${prep_gold}${prep_gate}${restore}
equiv_make gold gate equiv
equiv_simple equiv
equiv_induct equiv
equiv_status -assert equiv
"
  if run_yosys "$SCRIPT1" "$EQUIV_TMO"; then
    log_time "equiv_make+simple+induct" "$t0" "equivalent"
    pass_method "equiv_make+simple+induct"
  fi
  if [[ "${RC:-1}" -eq 124 ]]; then
    log_time "equiv_make+simple+induct" "$t0" "timeout"
  else
    log_time "equiv_make+simple+induct" "$t0" "unproven"
  fi
  echo "equiv_ref note: default equiv_* left unproven cells; trying -seq/-undef/equiv_struct"

  t0="$(sec_now)"
  SCRIPT2="${prep_gold}${prep_gate}${restore}
equiv_make gold gate equiv
equiv_simple -seq 8 -undef equiv
equiv_struct equiv
equiv_simple -seq 8 equiv
equiv_induct equiv
equiv_status -assert equiv
"
  if run_yosys "$SCRIPT2" "$EQUIV_TMO"; then
    log_time "equiv_simple -seq 8" "$t0" "equivalent"
    pass_method "equiv_simple -seq 8 -undef + equiv_struct + induct"
  fi
  if [[ "${RC:-1}" -eq 124 ]]; then
    log_time "equiv_simple -seq 8" "$t0" "timeout"
  else
    log_time "equiv_simple -seq 8" "$t0" "unproven"
  fi
  echo "equiv_ref note: still unproven; trying miter -equiv + sat -tempinduct"
fi

# 2) miter + sat -tempinduct
if has_method sat; then
  t0="$(sec_now)"
  SCRIPT3="${prep_gold}${prep_gate}${restore}
miter -equiv -flatten -make_assert gold gate miter
hierarchy -top miter
sat -verify -tempinduct -prove-asserts -set-init-zero -timeout $EQUIV_TMO
"
  if run_yosys "$SCRIPT3" "$((EQUIV_TMO + 15))"; then
    log_time "miter+sat-tempinduct" "$t0" "equivalent"
    pass_method "miter -equiv -flatten -make_assert + sat -tempinduct -prove-asserts -set-init-zero"
  fi
  fail_if_cex "sat-tempinduct" "${OUT:-}"
  if [[ "${RC:-1}" -eq 124 ]]; then
    log_time "miter+sat-tempinduct" "$t0" "timeout"
  else
    log_time "miter+sat-tempinduct" "$t0" "unproven"
  fi
  echo "equiv_ref note: output-only tempinduct did not finish; pairing hidden CRC and retrying"

  t0="$(sec_now)"
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
    log_time "sat-tempinduct-paired-crc" "$t0" "equivalent"
    pass_method "equiv_add crc + miter -assert + sat -tempinduct -prove-asserts -set-init-zero"
  fi
  fail_if_cex "sat-tempinduct-paired-crc" "${OUT:-}"
  if [[ "${RC:-1}" -eq 124 ]]; then
    log_time "sat-tempinduct-paired-crc" "$t0" "timeout"
  else
    log_time "sat-tempinduct-paired-crc" "$t0" "unproven"
  fi
  echo "equiv_ref note: sat -tempinduct unproven; trying ABC dsec|&cec"
fi

# 3) ABC dsec / &cec. Affine basis is not a recognized pass.
if has_method abc; then
  try_abc || true
fi

# 4) Auto register pairing (normalized Q names) + name-paired miter + reset.
# Pairing / port-name-set / reset mismatches are FAIL. Next-state (D) mismatch
# with those three OK is INCONCLUSIVE(state-encoding): switch to uncut
# output-only sequential proof. That proof must induct; BMC-only is 未证完.
REGPAIR_INCONCLUSIVE=0
try_regpair() {
  local t0 tmp abc_bin py extra=()
  t0="$(sec_now)"
  abc_bin="$(command -v yosys-abc || true)"
  py="$ROOT/scripts/gate/equiv_regpair.py"
  if [[ ! -f "$py" ]]; then
    echo "equiv_ref note: equiv_regpair.py missing"
    log_time "regpair" "$t0" "unproven"
    return 1
  fi
  if [[ -z "$abc_bin" ]]; then
    echo "equiv_ref note: yosys-abc not on PATH; regpair unproven"
    log_time "regpair" "$t0" "unproven"
    return 1
  fi
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/equiv_ref_regpair.XXXXXX")"
  echo "equiv_ref note: trying register pairing + name-paired miter (sat/ABC)"
  if [[ -n "${EQUIV_REGPAIR_OMIT_PO:-}" ]]; then
    extra+=(--omit-po "$EQUIV_REGPAIR_OMIT_PO")
    extra+=(--omit-side "${EQUIV_REGPAIR_OMIT_SIDE:-gold}")
  fi
  local dump="${prep_gold}${prep_gate}
design -load gold
autoname
write_json ${tmp}/gold.json
write_rtlil ${tmp}/gold.il
design -load gate
autoname
write_json ${tmp}/gate.json
write_rtlil ${tmp}/gate.il
"
  set +e
  if ! run_yosys "$dump" "$EQUIV_TMO"; then
    set -e
    echo "equiv_ref note: flatten/JSON dump failed or timed out"
    log_time "regpair" "$t0" "timeout"
    rm -rf "$tmp"
    return 1
  fi
  set -e
  if [[ ! -s "${tmp}/gold.json" || ! -s "${tmp}/gate.json" ]]; then
    echo "equiv_ref note: empty JSON for regpair"
    log_time "regpair" "$t0" "unproven"
    rm -rf "$tmp"
    return 1
  fi
  set +e
  python3 "$py" --leaf "$LEAF" --tmp "$tmp" --abc "$abc_bin" --tmo "$EQUIV_TMO" "${extra[@]}"
  local prc=$?
  set -e
  if [[ "$prc" -eq 0 ]]; then
    log_time "regpair" "$t0" "equivalent"
    rm -rf "$tmp"
    pass_method "regpair + miter -equiv -make_assert + sat/ABC (name-paired; reset checked)"
  fi
  if [[ "$prc" -eq 3 ]]; then
    echo "equiv_ref REGPAIR regpair=INCONCLUSIVE(state-encoding)"
    echo "equiv_ref note: next-state differs with same encoding interface; switching to uncut output seq"
    log_time "regpair" "$t0" "inconclusive"
    REGPAIR_INCONCLUSIVE=1
    rm -rf "$tmp"
    return 0
  fi
  if [[ "$prc" -eq 124 ]]; then
    log_time "regpair" "$t0" "timeout"
    rm -rf "$tmp"
    return 1
  fi
  log_time "regpair" "$t0" "not_equivalent"
  rm -rf "$tmp"
  echo "equiv_ref METHOD=regpair" >&2
  echo "equiv_ref FAIL ${LEAF} vs $(basename "$NET") (regpair: pairing/ports/reset)" >&2
  exit 1
}

# Uncut FFs. Miter asserts leaf outputs only. From reset. Induction must
# converge to pass. BMC to N with no CEX is 未证完 and FAIL (never a pass).
try_seq_out() {
  local t0 tmp abc_bin tmo depth rst_at script_seq script_bmc log rc kind
  t0="$(sec_now)"
  tmo="$EQUIV_TMO"
  depth="${EQUIV_SEQ_DEPTH:-16}"
  abc_bin="$(command -v yosys-abc || true)"
  rst_at=""
  case "$LEAF" in
    ub_dll_bcrc|ub_dll_bcrc_check) rst_at="-set-at 1 in_rst_pyc 1 -set-at 2 in_rst_pyc 1" ;;
  esac
  echo "equiv_ref note: uncut output-only seq from reset (induction required; BMC-only=未证完)"

  # BMC first: a CEX is a real output FAIL. Clean BMC is not a pass.
  t0="$(sec_now)"
  script_bmc="${prep_gold}${prep_gate}${restore}
miter -equiv -flatten -make_assert gold gate miter
hierarchy -top miter
sat -seq ${depth} -verify -prove-asserts -set-init-zero ${rst_at} -timeout ${tmo}
"
  echo "equiv_ref note: BMC depth=${depth} (CEX = FAIL; no CEX continues to induction)"
  if run_yosys "$script_bmc" "$((tmo + 15))"; then
    log_time "seq-bmc" "$t0" "no_cex"
    echo "equiv_ref SEQ bmc_depth=${depth} result=no_cex"
  else
    fail_if_cex "seq-bmc" "${OUT:-}"
    if [[ "${RC:-1}" -eq 124 ]]; then
      log_time "seq-bmc" "$t0" "timeout"
    else
      log_time "seq-bmc" "$t0" "unproven"
    fi
  fi

  t0="$(sec_now)"
  script_seq="${prep_gold}${prep_gate}${restore}
miter -equiv -flatten -make_assert gold gate miter
hierarchy -top miter
sat -verify -tempinduct -prove-asserts -set-init-zero ${rst_at} -timeout ${tmo}
"
  if run_yosys "$script_seq" "$((tmo + 15))"; then
    log_time "seq-tempinduct" "$t0" "equivalent"
    pass_method "uncut output miter + sat -tempinduct -prove-asserts (reset-init)"
  fi
  fail_if_cex "seq-tempinduct" "${OUT:-}"
  if [[ "${RC:-1}" -eq 124 ]]; then
    log_time "seq-tempinduct" "$t0" "timeout"
  else
    log_time "seq-tempinduct" "$t0" "unproven"
  fi

  if [[ -n "$abc_bin" ]]; then
    tmp="$(mktemp -d "${TMPDIR:-/tmp}/equiv_ref_seq.XXXXXX")"
    local script_aig="${prep_gold}${prep_gate}${restore}
miter -equiv -flatten -make_assert gold gate miter
hierarchy -top miter
delete t:\$assert t:\$assume t:\$live t:\$fair
techmap; opt; aigmap; opt
write_aiger -symbols -miter ${tmp}/miter.aig
"
    t0="$(sec_now)"
    set +e
    run_yosys "$script_aig" "$tmo"
    set -e
    if [[ -s "${tmp}/miter.aig" ]]; then
      for cmd in "pdr" "dprove"; do
        log="${tmp}/${cmd}.log"
        set +e
        timeout "$tmo" "$abc_bin" -c "read ${tmp}/miter.aig; ${cmd}" >"$log" 2>&1
        rc=$?
        set -e
        cat "$log"
        kind="$(abc_parse "$log")"
        if [[ "$kind" == equivalent ]]; then
          log_time "seq-abc-${cmd}" "$t0" "equivalent"
          rm -rf "$tmp"
          pass_method "uncut output miter + ABC ${cmd}"
        fi
        if [[ "$kind" == not_equivalent ]]; then
          log_time "seq-abc-${cmd}" "$t0" "not_equivalent"
          rm -rf "$tmp"
          echo "equiv_ref METHOD=seq-abc-${cmd}" >&2
          echo "equiv_ref FAIL ${LEAF} vs $(basename "$NET") (ABC ${cmd}: not equivalent)" >&2
          exit 1
        fi
      done
    fi
    rm -rf "$tmp"
  fi

  echo "equiv_ref SEQ 未证完 (BMC ${depth} cycles, induction did not converge)"
  echo "equiv_ref METHOD=seq-unproven" >&2
  echo "equiv_ref FAIL ${LEAF} vs $(basename "$NET") (seq: 未证完 BMC=${depth})" >&2
  exit 1
}

if has_method regpair; then
  try_regpair || true
fi

if [[ "${REGPAIR_INCONCLUSIVE}" -eq 1 ]] || has_method seq; then
  try_seq_out
fi

echo "equiv_ref METHOD=unproven" >&2
echo "equiv_ref FAIL ${LEAF} vs $(basename "$NET")" >&2
exit 1
