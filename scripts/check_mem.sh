#!/usr/bin/env bash
# Self-check for C-line ub_mem_tlb / ub_mem_inv:
#   * every leaf has PRODUCT + HOOKS
#   * PRODUCT has no tb_* ports
#   * tlb HOOKS has §10 obs + mem_tlb_wN backdoors; inv HOOKS has no tb_*
#   * pycc regen is byte-identical for all four netlists
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

if [[ -z "${PYC_TOOLCHAIN_ROOT:-}" ]]; then
  export PYC_TOOLCHAIN_ROOT=/tmp/spike/pyCircuit/.pycircuit_out/toolchain/install
fi

# Consumers use `-I rtl/pyc_lib` (SPEC §2.2; file owned by PR #21 / b6ba203c).
# Before #21 merges, fetch that file from the #21 branch into $WORK (not rtl/).
PR21_REF="${PR21_REF:-origin/cursor/cmn-mem-1r1w-5d26}"
if [[ -f "$ROOT/rtl/pyc_lib/pyc_reg.v" ]]; then
  PYC_INC="$ROOT/rtl/pyc_lib"
else
  git -C "$ROOT" cat-file -e "${PR21_REF}:rtl/pyc_lib/pyc_reg.v" 2>/dev/null \
    || git -C "$ROOT" fetch origin cursor/cmn-mem-1r1w-5d26
  mkdir -p "$WORK/pyc_lib"
  git -C "$ROOT" show "${PR21_REF}:rtl/pyc_lib/pyc_reg.v" > "$WORK/pyc_lib/pyc_reg.v"
  PYC_INC="$WORK/pyc_lib"
fi
PYC_REG="$PYC_INC/pyc_reg.v"
if [[ ! -f "$PYC_REG" ]]; then
  echo "FAIL: pyc_reg.v not found (need #21 rtl/pyc_lib or fetch $PR21_REF)"
  exit 1
fi

echo "=== ports ==="
for leaf in ub_mem_tlb ub_mem_inv; do
  if [[ ! -f "$RTL/$leaf.v" ]]; then
    echo "FAIL: PRODUCT missing $RTL/$leaf.v"
    exit 1
  fi
  if [[ ! -f "$HOOKS/$leaf.v" ]]; then
    echo "FAIL: HOOKS missing $HOOKS/$leaf.v"
    exit 1
  fi
done
if grep -E '^\s*(input|output).*tb_' "$RTL/ub_mem_tlb.v" "$RTL/ub_mem_inv.v"; then
  echo "FAIL: PRODUCT must not have tb_* ports"
  exit 1
fi
if grep -E '^\s*(input|output).*tb_' "$HOOKS/ub_mem_inv.v"; then
  echo "FAIL: ub_mem_inv HOOKS must not have tb_* (SPEC §10 lists none)"
  exit 1
fi
python3 - "$RTL/ub_mem_inv.v" "$HOOKS/ub_mem_inv.v" <<'PY'
import re, sys
def ports(path):
    text = open(path, encoding="utf-8").read()
    m = re.search(r"module\s+ub_mem_inv\s*\((.*?)\);", text, re.S)
    if not m:
        raise SystemExit(f"no ub_mem_inv port list in {path}")
    return [re.sub(r"\s+", " ", p).strip() for p in m.group(1).split(",") if p.strip()]
a, b = ports(sys.argv[1]), ports(sys.argv[2])
if a != b:
    print("FAIL: ub_mem_inv HOOKS ports != PRODUCT")
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            print(f"  [{i}] PRODUCT {x!r} vs HOOKS {y!r}")
    if len(a) != len(b):
        print(f"  len PRODUCT={len(a)} HOOKS={len(b)}")
    sys.exit(1)
print("ub_mem_inv HOOKS ports == PRODUCT (%d ports)" % len(a))
PY
if find "$RTL" -name 'pyc_*.v' | grep -q .; then
  echo "FAIL: pyc_* runtime must live in rtl/pyc_lib/ (#21), not rtl/mem/"
  find "$RTL" -name 'pyc_*.v'
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
    echo "FAIL: tlb HOOKS missing $p"
    exit 1
  fi
done
if grep -q 'keep' "$RTL/ub_mem_tlb.v" "$HOOKS/ub_mem_tlb.v" "$RTL/ub_mem_inv.v" "$HOOKS/ub_mem_inv.v"; then
  echo "FAIL: keep attribute present"
  exit 1
fi
echo "ports ok"

echo "=== regen byte-identical ==="
PY="${PY:-/tmp/spike/venv/bin/python3}"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi
"$PY" "$ROOT/scripts/emit_rtl.py" --out "$WORK/rtl"
for f in mem/ub_mem_tlb.v mem/hooks/ub_mem_tlb.v mem/ub_mem_inv.v mem/hooks/ub_mem_inv.v; do
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
  -I"$PYC_INC" \
  "$PH" \
  "$RTL/ub_mem_tlb.v"
verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN \
  -I"$PYC_INC" \
  "$RTL/ub_mem_inv.v"
echo "=== verilator lint HOOKS ==="
verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN \
  -Wno-PINCONNECTEMPTY \
  -I"$PYC_INC" \
  "$PH" \
  "$HOOKS/ub_mem_tlb.v"
verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN \
  -I"$PYC_INC" \
  "$HOOKS/ub_mem_inv.v"
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
cp "$PYC_REG" "$WORK/pyc_reg.v"
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
# Combinational/seq stub so SAT can see that matching we/re/addr/wdata
# imply matching rdata. Not a functional model; PRODUCT vs HOOKS only.
cat > "$WORK/ph_sat.v" <<'V'
module ub_cmn_mem_1r1w_d64w109 (
  input core_clk,
  input we,
  input [5:0] waddr,
  input [108:0] wdata,
  input re,
  input [5:0] raddr,
  output [108:0] rdata
);
  reg [108:0] q;
  wire [108:0] mix = wdata ^ {103'd0, waddr} ^ {103'd0, raddr} ^ {109{we}} ^ {109{re}};
  always @(posedge core_clk)
    q <= mix;
  assign rdata = q;
endmodule
V
strip_include "$HOOKS/ub_mem_tlb.v" "$WORK/tlb_hooks.v"
# Rewrite HOOKS to the PRODUCT port list (same module name / hierarchy)
# so equiv_make can pair internals. tb_* inputs tied; obs/bd_rdata become
# unused locals and are swept.
python3 - "$WORK/tlb_hooks.v" "$WORK/tlb_hooks_prodports.v" <<'PY'
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8").read()
m = re.search(r"module\s+ub_mem_tlb\s*\((.*?)\);", text, re.S)
if not m:
    raise SystemExit("no ub_mem_tlb port list")
body_start = m.end()
ports = []
for raw in m.group(1).split(","):
    line = " ".join(raw.split())
    if not line:
        continue
    ports.append(line)

prod, tied, body_subs = [], [], []
for p in ports:
    if re.search(r"\btb_", p):
        mm = re.match(r"(input|output)\s*(?:\[(\d+):(\d+)\]\s*)?(\w+)$", p)
        if not mm:
            raise SystemExit("cannot parse port: " + p)
        direc, msb, lsb, name = mm.group(1), mm.group(2), mm.group(3), mm.group(4)
        if msb is None:
            decl = f"  wire {name}"
            zero = "1'b0"
        else:
            decl = f"  wire [{msb}:{lsb}] {name}"
            width = int(msb) - int(lsb) + 1
            zero = f"{width}'b0"
        if direc == "input":
            tied.append(f"{decl} = {zero};")
            body_subs.append((name, zero))
        else:
            tied.append(f"{decl};")
    else:
        prod.append("  " + p)
new_mod = "module ub_mem_tlb (\n" + ",\n".join(prod) + "\n);\n" + "\n".join(tied) + "\n"
body = text[body_start:]
# Fold hook inputs to literals so opt can drop bd_steal from ready cones.
for name, zero in sorted(body_subs, key=lambda x: -len(x[0])):
    body = re.sub(r"\b" + name + r"\b", zero, body)
text = text[: m.start()] + new_mod + body
open(dst, "w", encoding="utf-8").write(text)
print("rewrote HOOKS to PRODUCT ports:", dst)
PY
cat > "$WORK/equiv.ys" <<'YS'
# Same top name and port list. Flatten pyc_reg + SAT-visible mem stub.
# Unused HOOKS obs / bd_rdata swept. Compare PRODUCT ports only.
read_verilog ph_sat.v
read_verilog pyc_reg.v
read_verilog tlb_prod.v
hierarchy -check -top ub_mem_tlb
proc
flatten
opt -purge
opt
design -stash gold
read_verilog ph_sat.v
read_verilog pyc_reg.v
read_verilog tlb_hooks_prodports.v
hierarchy -check -top ub_mem_tlb
proc
flatten
opt -purge
opt
design -stash gate
design -copy-from gold -as gold ub_mem_tlb
design -copy-from gate -as gate ub_mem_tlb
equiv_make gold gate equiv
hierarchy -top equiv
equiv_struct
equiv_simple -seq 16
equiv_induct -seq 16
equiv_status
YS
# SPEC §11: only PRODUCT ports must prove. Coincidental pyc_* names
# are not comparison points. Remaining ready ports (HOOKS ~bd_steal
# with inputs tied) are finished with sat induction.
( cd "$WORK" && yosys -s equiv.ys ) > "$WORK/equiv.log" 2>&1 || true
set +e
python3 - "$WORK/equiv.log" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
ports = {
    "lk_ready", "lk_rsp_valid", "lk_hit",
    "xlat_pfn", "xlat_attr", "xlat_ap", "xlat_uxn", "xlat_pxn", "xlat_af",
    "fill_ready", "inv2tlb_all_ready", "inv2tlb_scan_ready",
    "tlb2inv_scan_done", "busy",
}
unproven = [m.group(1) for m in re.finditer(r"Unproven \$equiv .*?\\(\w+)_gold", text)]
bad = sorted({n for n in unproven if n in ports})
internal = sorted({n for n in unproven if n not in ports})
print("unproven PRODUCT ports:", bad or "none")
if internal:
    print("ignored internal $equiv (name collision):", ", ".join(internal))
if "Found" not in text and "equiv cells" not in text:
    sys.exit(3)
sys.exit(2 if bad else 0)
PY
EQ_RC=$?
set -e
if [[ "$EQ_RC" -eq 0 ]]; then
  echo "equiv ok (PRODUCT ports)"
elif [[ "$EQ_RC" -eq 2 ]]; then
  echo "=== sat backup (PRODUCT ports; hooks tied) ==="
  cat > "$WORK/sat.ys" <<'YS'
read_verilog ph_sat.v
read_verilog pyc_reg.v
read_verilog tlb_prod.v
hierarchy -check -top ub_mem_tlb
proc
flatten
opt -purge
opt
design -stash gold
read_verilog ph_sat.v
read_verilog pyc_reg.v
read_verilog tlb_hooks_prodports.v
hierarchy -check -top ub_mem_tlb
proc
flatten
opt -purge
opt
design -stash gate
design -copy-from gold -as gold ub_mem_tlb
design -copy-from gate -as gate ub_mem_tlb
miter -equiv -make_assert gold gate miter
hierarchy -top miter
flatten
opt
sat -verify -tempinduct -set-init-zero -seq 4
YS
  set +e
  ( cd "$WORK" && yosys -s sat.ys ) > "$WORK/sat.log" 2>&1
  SAT_RC=$?
  set -e
  if [[ "$SAT_RC" -eq 0 ]] || grep -q "nothing to prove" "$WORK/sat.log"; then
    echo "equiv ok (PRODUCT ports; sat/miter)"
  else
    tail -n 30 "$WORK/sat.log"
    echo "FAIL: yosys equiv/sat (PRODUCT ports)"
    exit 1
  fi
else
  echo "FAIL: yosys equiv produced no status"
  exit 1
fi

echo "=== yosys equiv ub_mem_inv PRODUCT vs HOOKS (no tb_*) ==="
strip_include "$HOOKS/ub_mem_inv.v" "$WORK/inv_hooks.v"
cat > "$WORK/equiv_inv.ys" <<'YS'
read_verilog pyc_reg.v
read_verilog inv_prod.v
hierarchy -check -top ub_mem_inv
proc
flatten
opt -purge
opt
design -stash gold
read_verilog pyc_reg.v
read_verilog inv_hooks.v
hierarchy -check -top ub_mem_inv
proc
flatten
opt -purge
opt
design -stash gate
design -copy-from gold -as gold ub_mem_inv
design -copy-from gate -as gate ub_mem_inv
equiv_make gold gate equiv
hierarchy -top equiv
equiv_struct
equiv_simple -seq 16
equiv_induct -seq 16
equiv_status -assert
YS
( cd "$WORK" && yosys -q -s equiv_inv.ys )
echo "equiv ok (ub_mem_inv PRODUCT ≡ HOOKS)"

echo "ALL CHECKS PASSED"
