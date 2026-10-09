# pyCircuit sources (M1 leaf batch 1)

Product RTL except whitelist `ub_rst_sync` is generated from this tree.
Pin: [`TOOLCHAIN.lock`](TOOLCHAIN.lock) (`lukebest/pyCircuit` @ `43cc5918`, pyc4.0).

```bash
make emit        # write rtl/gen/**/*.v  (TEST_HOOKS=0)
make selfcheck   # emit + Python golden (not a TB)
make lint        # Verilator --lint-only -Wall
make synth       # Yosys read / hierarchy / proc
```

Do not put the repo root on `PYTHONPATH` (the toolchain package is also
named `pycircuit`). `pycircuit/emit.py` puts only this directory on `sys.path`.

Generated files land under `rtl/gen/` so D10 legacy `rtl/{pcs,dll}/*.v` is
not overwritten. Whitelist SV: `rtl/common/ub_rst_sync.sv`.
