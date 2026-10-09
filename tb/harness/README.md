# TB-only harness

`tb_passthru_hooks0.sv` and `tb_passthru_hooks1.sv` are **not product RTL**.
They exist so the uvm-python skeleton can run on Icarus / Verilator without
`rtl/`. Do not move these files into `rtl/`. Product netlists are generated
by pyCircuit with `TEST_HOOKS` expanded in Python (SPEC §11), not by this
harness.

| File | Role |
| --- | --- |
| `tb_passthru_hooks0.sv` | Stand-in for PRODUCT (`TEST_HOOKS=0`): no `tb_*` ports |
| `tb_passthru_hooks1.sv` | Stand-in for HOOKS (`TEST_HOOKS=1`): SPEC §10 ports, gated by `tb_test_mode` |
