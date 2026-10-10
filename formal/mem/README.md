# `formal/mem/` — `ub_mem_tlb` observation assertions

Verification-C. Bindable properties on the HOOKS netlist (SPEC §10 obs
ports). Yosys-compatible clocked `assert`/`cover`. Not product RTL.

| File | Role |
| --- | --- |
| `ub_mem_tlb_if_props.sv` | Assert: `$onehot0(obs_hit)`; hit implies valid; valid-way tags pairwise distinct. Only when `tb_mem_tlb_obs_lkup_v=1`. Cover: per-way hit, all-four valid lookup, two same-tag fills then hit. |
| `ub_mem_tlb_harness.sv` | Instantiates HOOKS `ub_mem_tlb` + props. `rst_pyc` high 4 cycles; `tb_test_mode=0`; backdoor inputs tied. Other inputs free. |
| `ub_mem_tlb.sby` | BMC + cover, depth 32 (see file header). |
| `get_pyc_inc.sh` | Same `pyc_reg.v` resolution as `scripts/check_mem.sh`: `rtl/pyc_lib` or PR #21 `origin/cursor/cmn-mem-1r1w-5d26`. Writes `inc/pyc_reg.v`. |

Reads the PR #27 hooks netlist and `tb/mem/lint_placeholder/ub_cmn_mem_1r1w_d64w109.v`. After PR #21 merges, delete `inc/` / the helper and point the primitive + `pyc_reg` at main (`-I rtl/pyc_lib`).

```
bash formal/mem/get_pyc_inc.sh
sby -f formal/mem/ub_mem_tlb.sby
```

Engine: `smtbmc --nounroll boolector` (Yosys 0.33 + `--unroll` BrokenPipe). Run `sby -f --sequential` on 16 GB.
