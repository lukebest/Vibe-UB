#!/usr/bin/env bash
# Self-check for C-line ub_mem_tlb / ub_mem_inv:
#   * PRODUCT has no tb_* ports
#   * HOOKS has §10 obs + mem_tlb_wN backdoors
#   * pycc regen is byte-identical
#   * Verilator lint (PRODUCT + HOOKS)
#   * Yosys synth (PRODUCT, primitive black-boxed)
#   * Yosys equiv: PRODUCT ports only (HOOKS tb_test_mode=0, bd inputs tied)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RTL="$ROOT/rtl/mem"
HOOKS="$RTL/hooks"
PH="$ROOT/tb/mem/lint_placeholder/ub_cmn_mem_1r1w_d64w109.v"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/ub_mem_check.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

strip_include() {
  grep -v '^`include "pyc_reg.v"' "$1" > "$2"
}

echo "=== ports ==="
if grep -E '^\s*(input|output).*tb_' "$RTL/ub_mem_tlb.v" "$RTL/ub_mem_inv.v"; then
  echo "FAIL: PRODUCT must not have tb_* ports"
  exit 1
fi
for p in \
  tb_mem_tlb_obs_lkup_v \
  tb_mem_tlb_obs_hit \
  tb_mem_tlb_obs_vld \
  tb_mem_tlb_obs_tag_w0 \
  tb_mem_tlb_obs_tag_w1 \
  tb_mem_tlb_obs_tag_w2 \
  tb_mem_tlb_obs_tag_w3 \
  tb_test_mode \
  tb_mem_tlb_w0_bd_we tb_mem_tlb_w0_bd_addr tb_mem_tlb_w0_bd_wdata tb_mem_tlb_w0_bd_re tb_mem_tlb_w0_bd_rdata \
  tb_mem_tlb_w0_bd_vld_we tb_mem_tlb_w0_bd_vld_wdata \
  tb_mem_tlb_w1_bd_we tb_mem_tlb_w1_bd_rdata tb_mem_tlb_w1_bd_vld_we \
  tb_mem_tlb_w2_bd_we tb_mem_tlb_w2_bd_rdata tb_mem_tlb_w2_bd_vld_we \
  tb_mem_tlb_w3_bd_we tb_mem_tlb_w3_bd_rdata tb_mem_tlb_w3_bd_vld_we
do
  if ! grep -q "$p" "$HOOKS/ub_mem_tlb.v"; then
    echo "FAIL: HOOKS missing $p"
    exit 1
  fi
done
if grep -q 'keep' "$RTL/ub_mem_tlb.v" "$HOOKS/ub_mem_tlb.v"; then
  echo "FAIL: keep attribute present"
  exit 1
fi
echo "ports ok"

echo "=== regen byte-identical ==="
if [[ -z "${PYC_TOOLCHAIN_ROOT:-}" ]]; then
  export PYC_TOOLCHAIN_ROOT=/tmp/spike/pyCircuit/.pycircuit_out/toolchain/install
fi
PY="${PY:-/tmp/spike/venv/bin/python3}"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi
"$PY" "$ROOT/scripts/emit_rtl.py" --out "$WORK/rtl"
for f in mem/ub_mem_tlb.v mem/hooks/ub_mem_tlb.v mem/ub_mem_inv.v mem/pyc_reg.v; do
  if ! diff -q "$ROOT/rtl/$f" "$WORK/rtl/$f"; then
    echo "FAIL: regen mismatch $f"
    diff -u "$ROOT/rtl/$f" "$WORK/rtl/$f" | head -n 80
    exit 1
  fi
done
echo "regen ok"

echo "=== verilator lint PRODUCT ==="
verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN \
  -Wno-PINCONNECTEMPTY \
  -I"$RTL" \
  "$PH" \
  "$RTL/ub_mem_tlb.v"
verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN \
  -I"$RTL" \
  "$RTL/ub_mem_inv.v"
echo "=== verilator lint HOOKS ==="
verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN \
  -Wno-PINCONNECTEMPTY \
  -I"$RTL" \
  "$PH" \
  "$HOOKS/ub_mem_tlb.v"
echo "lint ok"

echo "=== yosys synth PRODUCT (primitive black-box) ==="
strip_include "$RTL/ub_mem_tlb.v" "$WORK/tlb_prod.v"
strip_include "$RTL/ub_mem_inv.v" "$WORK/inv_prod.v"
cat > "$WORK/synth.ys" <<'YS'
read_verilog -lib ph.v
read_verilog pyc_reg.v
read_verilog tlb_prod.v
hierarchy -check -top ub_mem_tlb
proc
opt
memory
opt
check -assert
stat
select -assert-none t:$dlatch t:$adff
YS
cp "$PH" "$WORK/ph.v"
cp "$RTL/pyc_reg.v" "$WORK/pyc_reg.v"
( cd "$WORK" && yosys -q -s synth.ys )
cat > "$WORK/synth_inv.ys" <<'YS'
read_verilog pyc_reg.v
read_verilog inv_prod.v
hierarchy -check -top ub_mem_inv
proc
opt
check -assert
stat
select -assert-none t:$dlatch t:$adff
YS
( cd "$WORK" && yosys -q -s synth_inv.ys )
echo "synth ok"

echo "=== yosys equiv PRODUCT ports only ==="
strip_include "$HOOKS/ub_mem_tlb.v" "$WORK/tlb_hooks.v"
# Wrapper: HOOKS with tb_test_mode=0 and all bd_* inputs tied; only PRODUCT ports.
python3 - <<'PY' > "$WORK/tlb_hooks_wrap.v"
print("""module ub_mem_tlb_hooks_gold (
  input core_clk,
  input rst_pyc,
  input lk_valid,
  input [3:0] lk_ent_idx,
  input [19:0] lk_token_id,
  input [35:0] lk_page,
  input fill_valid,
  input [3:0] fill_ent_idx,
  input [19:0] fill_token_id,
  input [35:0] fill_page,
  input [35:0] fill_pfn,
  input [7:0] fill_attr,
  input [1:0] fill_ap,
  input fill_uxn,
  input fill_pxn,
  input fill_af,
  input inv2tlb_all_valid,
  input inv2tlb_scan_valid,
  input [5:0] inv2tlb_scan_set,
  input [3:0] inv2tlb_scan_ent_idx,
  input [19:0] inv2tlb_scan_token_id,
  input inv2tlb_scan_match_ent,
  input inv2tlb_scan_match_tok,
  output lk_ready,
  output lk_rsp_valid,
  output lk_hit,
  output [35:0] xlat_pfn,
  output [7:0] xlat_attr,
  output [1:0] xlat_ap,
  output xlat_uxn,
  output xlat_pxn,
  output xlat_af,
  output fill_ready,
  output inv2tlb_all_ready,
  output inv2tlb_scan_ready,
  output tlb2inv_scan_done,
  output busy
);
  wire obs_lkup_v;
  wire [3:0] obs_hit;
  wire [3:0] obs_vld;
  wire [59:0] obs_tag0, obs_tag1, obs_tag2, obs_tag3;
  wire [108:0] bd0, bd1, bd2, bd3;
  ub_mem_tlb u (
    .core_clk(core_clk),
    .rst_pyc(rst_pyc),
    .lk_valid(lk_valid),
    .lk_ent_idx(lk_ent_idx),
    .lk_token_id(lk_token_id),
    .lk_page(lk_page),
    .fill_valid(fill_valid),
    .fill_ent_idx(fill_ent_idx),
    .fill_token_id(fill_token_id),
    .fill_page(fill_page),
    .fill_pfn(fill_pfn),
    .fill_attr(fill_attr),
    .fill_ap(fill_ap),
    .fill_uxn(fill_uxn),
    .fill_pxn(fill_pxn),
    .fill_af(fill_af),
    .inv2tlb_all_valid(inv2tlb_all_valid),
    .inv2tlb_scan_valid(inv2tlb_scan_valid),
    .inv2tlb_scan_set(inv2tlb_scan_set),
    .inv2tlb_scan_ent_idx(inv2tlb_scan_ent_idx),
    .inv2tlb_scan_token_id(inv2tlb_scan_token_id),
    .inv2tlb_scan_match_ent(inv2tlb_scan_match_ent),
    .inv2tlb_scan_match_tok(inv2tlb_scan_match_tok),
    .tb_test_mode(1'b0),
    .tb_mem_tlb_w0_bd_we(1'b0),
    .tb_mem_tlb_w0_bd_addr(6'b0),
    .tb_mem_tlb_w0_bd_wdata(109'b0),
    .tb_mem_tlb_w0_bd_re(1'b0),
    .tb_mem_tlb_w0_bd_vld_we(1'b0),
    .tb_mem_tlb_w0_bd_vld_wdata(1'b0),
    .tb_mem_tlb_w1_bd_we(1'b0),
    .tb_mem_tlb_w1_bd_addr(6'b0),
    .tb_mem_tlb_w1_bd_wdata(109'b0),
    .tb_mem_tlb_w1_bd_re(1'b0),
    .tb_mem_tlb_w1_bd_vld_we(1'b0),
    .tb_mem_tlb_w1_bd_vld_wdata(1'b0),
    .tb_mem_tlb_w2_bd_we(1'b0),
    .tb_mem_tlb_w2_bd_addr(6'b0),
    .tb_mem_tlb_w2_bd_wdata(109'b0),
    .tb_mem_tlb_w2_bd_re(1'b0),
    .tb_mem_tlb_w2_bd_vld_we(1'b0),
    .tb_mem_tlb_w2_bd_vld_wdata(1'b0),
    .tb_mem_tlb_w3_bd_we(1'b0),
    .tb_mem_tlb_w3_bd_addr(6'b0),
    .tb_mem_tlb_w3_bd_wdata(109'b0),
    .tb_mem_tlb_w3_bd_re(1'b0),
    .tb_mem_tlb_w3_bd_vld_we(1'b0),
    .tb_mem_tlb_w3_bd_vld_wdata(1'b0),
    .lk_ready(lk_ready),
    .lk_rsp_valid(lk_rsp_valid),
    .lk_hit(lk_hit),
    .xlat_pfn(xlat_pfn),
    .xlat_attr(xlat_attr),
    .xlat_ap(xlat_ap),
    .xlat_uxn(xlat_uxn),
    .xlat_pxn(xlat_pxn),
    .xlat_af(xlat_af),
    .fill_ready(fill_ready),
    .inv2tlb_all_ready(inv2tlb_all_ready),
    .inv2tlb_scan_ready(inv2tlb_scan_ready),
    .tlb2inv_scan_done(tlb2inv_scan_done),
    .busy(busy),
    .tb_mem_tlb_obs_lkup_v(obs_lkup_v),
    .tb_mem_tlb_obs_hit(obs_hit),
    .tb_mem_tlb_obs_vld(obs_vld),
    .tb_mem_tlb_obs_tag_w0(obs_tag0),
    .tb_mem_tlb_obs_tag_w1(obs_tag1),
    .tb_mem_tlb_obs_tag_w2(obs_tag2),
    .tb_mem_tlb_obs_tag_w3(obs_tag3),
    .tb_mem_tlb_w0_bd_rdata(bd0),
    .tb_mem_tlb_w1_bd_rdata(bd1),
    .tb_mem_tlb_w2_bd_rdata(bd2),
    .tb_mem_tlb_w3_bd_rdata(bd3)
  );
endmodule
""")
PY
cat > "$WORK/equiv.ys" <<'YS'
read_verilog -lib ph.v
read_verilog pyc_reg.v
read_verilog tlb_prod.v
prep -top ub_mem_tlb
design -stash gold
read_verilog -lib ph.v
read_verilog pyc_reg.v
read_verilog tlb_hooks.v
read_verilog tlb_hooks_wrap.v
prep -top ub_mem_tlb_hooks_gold
design -stash gate
design -copy-from gold -as gold ub_mem_tlb
design -copy-from gate -as gate ub_mem_tlb_hooks_gold
equiv_make gold gate equiv
hierarchy -top equiv
equiv_simple
equiv_induct
equiv_status -assert
YS
( cd "$WORK" && yosys -q -s equiv.ys )
echo "equiv ok"

echo "ALL CHECKS PASSED"
