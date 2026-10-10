# `formal/cmn/` — `ub_cmn_mem_1r1w` interface assertions

Architecture-owned. CODING_STYLE §10 / PR #20 (Xia timing proposal).
Yosys-compatible clocked `assert`/`cover`. Not product RTL.

| File | Role |
| --- | --- |
| `ub_cmn_mem_1r1w_if_props.sv` | Bindable properties. `anyconst` address; written bit + data for that address only. `ASSERT_NO_UNINIT_READ` (default 1). |
| `ub_cmn_mem_1r1w_formal_ref.sv` | Formal-only synthesizable behavioral 1R1W. Design-B adds the pycc leaf. |
| `ub_cmn_mem_1r1w_harness.sv` | Env assumes (in-range; no uninit read of the watched address) so BMC converges. |
| `cmn.sby` | BMC + cover, DEPTH=5 (non-pow2), WIDTH=8 |

`make -C formal` runs every `formal/<iface>/<iface>.sby`.
