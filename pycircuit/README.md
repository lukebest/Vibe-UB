# pyCircuit sources (M1 leaf batch 1)

Product RTL except whitelist `ub_rst_sync` is generated from this tree.
Pin: [`TOOLCHAIN.lock`](TOOLCHAIN.lock) (`lukebest/pyCircuit` @ `43cc5918`, pyc4.0).

```bash
make emit        # PRODUCT + HOOKS via scripts/emit_rtl.py
make selfcheck   # emit + Python golden (not a TB)
make lint        # Verilator --lint-only -Wall on PRODUCT and HOOKS
make synth       # Yosys read / hierarchy / proc
make equiv       # PRODUCT vs HOOKS (eqy, else yosys equiv_*)
```

Layout (SPEC §2.2 / CODING_STYLE §5; same convention as `ub_lmsm`):

- PRODUCT (`TEST_HOOKS=0`) → `rtl/<block>/<module>.v`
- HOOKS (`TEST_HOOKS=1`) → `rtl/<block>/hooks/<module>.v`

SPEC §10 lists **no** hook ports on these leaves, so HOOKS is
port-identical to PRODUCT (header `TEST_HOOKS=1` only). Xia: no unused
`tb_test_mode` on leaves that §10 does not list.
Filename equals the module name (Verilator `DECLFILENAME`).
Later layers register in `scripts/emit_rtl.py`.

`ub_pcs_scrambler` / `ub_pcs_descrambler` OPEN items (SPEC §13: `SCR_TAPS`,
`SEED_MAP`, `LFSR_INIT`) have **no product default**. The emitted `.v`
syntax stubs are all-zero. Parent, `selfcheck.py`, `make lint`, and
`make synth` must pass explicit overrides (`pycircuit/lib/elab_open.py`).
Do not treat those tokens as SPEC values.

Do not put the repo root on `PYTHONPATH` (the toolchain package is also
named `pycircuit`). `pycircuit/emit.py` puts only this directory on `sys.path`.

Whitelist SV: `rtl/common/ub_rst_sync.sv`.
