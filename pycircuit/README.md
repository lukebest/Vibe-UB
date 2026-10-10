# pyCircuit sources (M1 leaf batch 1)

Product RTL except whitelist `ub_rst_sync` is generated from this tree.
Pin: root [`TOOLCHAIN.lock`](../TOOLCHAIN.lock) `[pycircuit]` (`lukebest/pyCircuit` @ `43cc5918`, pyc4.0 / pycc LLVM 19.1.1).

```bash
bash scripts/setup_pycircuit.sh   # once per machine
make emit        # PRODUCT + HOOKS via scripts/emit_rtl.py (pycc for STEP 1)
make selfcheck   # emit + Python golden (not a TB)
make lint        # Verilator --lint-only -Wall on PRODUCT and HOOKS
make synth       # Yosys read / hierarchy / proc
make equiv       # PRODUCT vs HOOKS (eqy, else yosys equiv_*)
```

Layout (SPEC §2.2 / CODING_STYLE §5):

- PRODUCT (`TEST_HOOKS=0`) → `rtl/<block>/<leaf>[_<tag>].v`
- HOOKS (`TEST_HOOKS=1`) → `rtl/<block>/hooks/<leaf>[_<tag>].v`
- Lane variants: `ub_pcs_lane_dist_x4` / `_x8` (and dedist). Untagged leftover `.v` removed.
- Single-config STEP 1 leaves stay untagged: `ub_pyc_rst_adapt`, `ub_dll_bcrc`, `ub_dll_bcrc_check`.

SPEC §10 lists **no** hook ports on these leaves, so HOOKS is
port-identical to PRODUCT. Xia: no unused `tb_test_mode`.

STEP 1 uses the real pyCircuit API + `compile()` +
`pycc --emit=verilog --logic-depth=64` (same invocation as PR #11).
STEP 2 pending:
`ub_pcs_scrambler` / `ub_pcs_descrambler` leftover f-string emitters
(files untouched). Their OPEN items (SPEC §13) still have no product
default; lint/synth pass `pycircuit/lib/elab_open.py` tokens.

Do not put the repo root on `PYTHONPATH` (the toolchain package is also
named pycircuit). `scripts/emit_rtl.py` re-execs `/tmp/venv/bin/python`
and puts only this directory on `sys.path`.

Whitelist SV: `rtl/common/ub_rst_sync.sv`.
