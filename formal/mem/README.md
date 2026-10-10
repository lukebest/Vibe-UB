# `formal/mem/` — `ub_mem_tlb` observation assertions

Verification-C. Bindable properties on the HOOKS netlist (SPEC §10 obs
ports). Yosys-compatible clocked `assert`/`cover`. Not product RTL.
`formal/mem/` has no Python (bash `get_pyc_inc.sh` + sby/SV only).

| File | Role |
| --- | --- |
| `ub_mem_tlb_if_props.sv` | 11 asserts + 6 covers (HOOKS ports). Unchanged. |
| `ub_mem_tlb_harness.sv` | HOOKS `ub_mem_tlb` + props. `rst_pyc` high 4 cycles; `tb_test_mode=0`; backdoors tied. |
| `ub_mem_tlb.sby` | Default tasks `cover` + `bmc`. |
| `get_pyc_inc.sh` | Same `pyc_reg.v` resolution as `scripts/check_mem.sh`. |

```
bash formal/mem/get_pyc_inc.sh
sby -f --sequential formal/mem/ub_mem_tlb.sby
```

Run from the **repo root** (`[files]` are root-relative; that matches `scripts/gate/formal.sh`).

## Default tasks (gate)

Engine: `smtbmc yices` (Yices 2.7). Timed on this VM:

| task | mode | depth | wall | result |
| --- | --- | --- | --- | --- |
| `cover` | cover | 20 | ~7 s | PASS, all 6 covers reached |
| `bmc` | bmc | 17 | ~62 s | PASS, all 11 asserts, no CEX |

Sequential total ≈ 70 s (budget ~10 min). `sby -f` without `--sequential` also fits: the two tasks do not share a solver.

Depth rationale: deepest cover is step 17 (`c_way3_hit`, `c_all_vld_lkup`). Cover uses 20 (17 + search margin). BMC uses 17 — yices at depth 18 already spends minutes on one step; z3 at step 16 took ~50 min.

### Engine bake-off (same design, this VM)

| engine | cover | bmc |
| --- | --- | --- |
| `smtbmc yices` | PASS, 7 s | PASS, 62 s (depth 17) |
| `smtbmc boolector` / `--nounroll` | ERROR, ~2 s, `BrokenPipeError` (apt 1.5 cannot eat this SMT2) | not run |
| `abc bmc3` | n/a | sby `KeyError: 'asserts'` after aiger (~15 s) |
| `smtbmc --nopresat z3` | PASS, ~6 min (depth 32) | still on step 16 at ~50 min |

## `prove` (not a default / gate task)

`sby -f` only runs `[tasks]` = `cover` `bmc`. k-induction (`smtbmc yices`, mode prove):

- basecase PASS (same as BMC depth 17, ~62 s)
- induction FAIL in 3 s on `a_tag_unique_13` — unreachable (arrays start arbitrary; asserts are gated by `obs_lkup_v`)
- `abc pdr`: same sby `KeyError` as `bmc3`

Left out of `[tasks]` so the gate stays inside the 10 min budget. Do not add a second `formal/mem/*.sby` (the gate walks every one).

## `pyc_reg.v`

#27 dropped `rtl/pyc_lib/`. `get_pyc_inc.sh` copies `rtl/pyc_lib/pyc_reg.v` or `origin/cursor/cmn-mem-1r1w-5d26:rtl/pyc_lib/pyc_reg.v` into `inc/`. After #21 merges, delete `inc/` / the helper and use `-I rtl/pyc_lib`.
