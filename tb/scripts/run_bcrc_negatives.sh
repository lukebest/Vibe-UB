#!/usr/bin/env bash
# Negative BCRC fixtures must FAIL both the leaf TB and equiv_ref.sh.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TB="$ROOT/tb"
SIM="${1:-icarus}"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export REF=0
if [[ -f "$ROOT/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/venv/bin/activate"
fi

DROP="$ROOT/formal/dll/negative/bcrc_drop_start_flit.sv"
FLIP="$ROOT/formal/dll/negative/bcrc_flip.sv"
FWD="$ROOT/formal/pcs/negative/forward_lane_dist.sv"
RST0="$ROOT/formal/dll/negative/bcrc_wrong_reset.sv"
EXTRA="$ROOT/formal/dll/negative/bcrc_extra_reg.sv"
CARRY="$ROOT/formal/dll/negative/bcrc_carry_after_last.sv"
GOLD="$ROOT/formal/dll/ref/ub_dll_bcrc.sv"

fail=0
expect_fail() {
  local name="$1"
  shift
  echo "=== expect FAIL: $name ==="
  local log
  log="$(mktemp)"
  set +e
  "$@" >"$log" 2>&1
  local rc=$?
  set -e
  tail -n 30 "$log"
  if [[ "$rc" -eq 0 ]]; then
    echo "NEG_MISS $name passed (should fail)"
    fail=$((fail + 1))
  elif ! grep -qE 'NOT EQUIVALENT|Assert failed|SAT proof finished|unmatched|ports=FAIL|regpair=FAIL|INCONCLUSIVE\(state-encoding\)|未证完|scoreboard|MISMATCH|equiv_ref FAIL|FAIL |Error|AssertionError' "$log"; then
    echo "NEG_MISS $name rc=$rc but no real compare conclusion"
    fail=$((fail + 1))
  else
    echo "NEG_OK $name rc=$rc"
  fi
  rm -f "$log"
}

expect_fail "tb drop-start-flit" \
    make -C "$TB" leaf SIM="$SIM" LEAF=ub_dll_bcrc TEST_HOOKS=0 REF=0 GATE_NET="$DROP"

expect_fail "tb carry-after-last" \
    make -C "$TB" leaf SIM="$SIM" LEAF=ub_dll_bcrc TEST_HOOKS=0 REF=0 GATE_NET="$CARRY"

# ABC path only: GATE-EQY-004 requires the three fakes to fail under dsec/&cec.
expect_fail "equiv_ref drop-start-flit (abc)" \
  env EQUIV_METHODS=abc EQUIV_TMO="${EQUIV_TMO:-30}" \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_dll_bcrc "$DROP"

expect_fail "equiv_ref crc-bit-flip (abc)" \
  env EQUIV_METHODS=abc EQUIV_TMO="${EQUIV_TMO:-30}" \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_dll_bcrc "$FLIP"

expect_fail "equiv_ref forward lane (abc)" \
  env EQUIV_METHODS=abc EQUIV_TMO="${EQUIV_TMO:-30}" NUM_LANES=4 \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_pcs_lane_dist "$FWD"

# GATE-EQY-004 (4): same fakes plus wrong-reset / extra-reg must fail under regpair.
# Gold versus gold must PASS.
expect_fail "equiv_ref drop-start-flit (regpair)" \
  env EQUIV_METHODS=regpair EQUIV_TMO="${EQUIV_TMO:-30}" \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_dll_bcrc "$DROP"

expect_fail "equiv_ref crc-bit-flip (regpair)" \
  env EQUIV_METHODS=regpair EQUIV_TMO="${EQUIV_TMO:-30}" \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_dll_bcrc "$FLIP"

expect_fail "equiv_ref wrong-reset (regpair)" \
  env EQUIV_METHODS=regpair EQUIV_TMO="${EQUIV_TMO:-30}" \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_dll_bcrc "$RST0"

expect_fail "equiv_ref extra-reg (regpair)" \
  env EQUIV_METHODS=regpair EQUIV_TMO="${EQUIV_TMO:-30}" \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_dll_bcrc "$EXTRA"

expect_fail "equiv_ref carry-after-last (abc)" \
  env EQUIV_METHODS=abc EQUIV_TMO="${EQUIV_TMO:-30}" \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_dll_bcrc "$CARRY"

expect_fail "equiv_ref carry-after-last (regpair)" \
  env EQUIV_METHODS=regpair EQUIV_TMO="${EQUIV_TMO:-30}" \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_dll_bcrc "$CARRY"

expect_fail "equiv_ref forward lane (regpair)" \
  env EQUIV_METHODS=regpair EQUIV_TMO="${EQUIV_TMO:-30}" NUM_LANES=4 \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_pcs_lane_dist "$FWD"

echo "=== expect PASS: gold vs gold (regpair) ==="
gold_log="$(mktemp)"
set +e
env EQUIV_METHODS=regpair EQUIV_TMO="${EQUIV_TMO:-30}" \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_dll_bcrc "$GOLD" >"$gold_log" 2>&1
gold_rc=$?
set -e
tail -n 40 "$gold_log"
if [[ "$gold_rc" -ne 0 ]] || ! grep -q 'equiv_ref PASS' "$gold_log"; then
  echo "NEG_MISS gold-vs-gold (regpair) should pass rc=$gold_rc"
  fail=$((fail + 1))
else
  echo "NEG_OK gold-vs-gold (regpair) rc=$gold_rc"
fi
rm -f "$gold_log"

echo "=== expect PASS: gold vs shuffled-port gold (regpair) ==="
shuf_sv="$(mktemp --suffix=_bcrc_shuffle.sv)"
python3 - "$GOLD" "$shuf_sv" <<'PY'
import re, sys
from pathlib import Path
src, dest = Path(sys.argv[1]), Path(sys.argv[2])
text = src.read_text(encoding="utf-8")
shuffled = (
    "module ub_dll_bcrc (\n"
    "  output reg          done,\n"
    "  input  wire         last,\n"
    "  output reg  [31:0]  crc_word,\n"
    "  input  wire [159:0] data_in,\n"
    "  input  wire         valid_in,\n"
    "  input  wire         start,\n"
    "  input  wire         rst_pyc,\n"
    "  input  wire         core_clk\n"
    ");"
)
new, n = re.subn(r"module\s+ub_dll_bcrc\s*\([^)]*\);", shuffled, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit(f"shuffle rewrite failed n={n}")
dest.write_text(new, encoding="utf-8")
PY
shuf_log="$(mktemp)"
set +e
env EQUIV_METHODS=regpair EQUIV_TMO="${EQUIV_TMO:-30}" \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_dll_bcrc "$shuf_sv" >"$shuf_log" 2>&1
shuf_rc=$?
set -e
tail -n 20 "$shuf_log"
if [[ "$shuf_rc" -ne 0 ]] || ! grep -q 'equiv_ref PASS' "$shuf_log"; then
  echo "NEG_MISS gold-vs-shuffle (regpair) should pass rc=$shuf_rc"
  fail=$((fail + 1))
else
  echo "NEG_OK gold-vs-shuffle (regpair) rc=$shuf_rc"
fi
rm -f "$shuf_sv" "$shuf_log"

echo "=== expect FAIL: omit rp_d_crc on gold (regpair ports) ==="
omit_log="$(mktemp)"
set +e
env EQUIV_METHODS=regpair EQUIV_TMO="${EQUIV_TMO:-30}" \
  EQUIV_REGPAIR_OMIT_PO=rp_d_crc EQUIV_REGPAIR_OMIT_SIDE=gold \
  "$ROOT/scripts/gate/equiv_ref.sh" ub_dll_bcrc "$GOLD" >"$omit_log" 2>&1
omit_rc=$?
set -e
tail -n 20 "$omit_log"
if [[ "$omit_rc" -eq 0 ]] || ! grep -q 'ports=FAIL' "$omit_log" || ! grep -q 'rp_d_crc' "$omit_log"; then
  echo "NEG_MISS omit-rp_d_crc should ports=FAIL and list rp_d_crc rc=$omit_rc"
  fail=$((fail + 1))
else
  echo "NEG_OK omit-rp_d_crc (regpair) rc=$omit_rc"
fi
rm -f "$omit_log"

echo "=== bcrc negatives miss=$fail ==="
exit "$fail"
