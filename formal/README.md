# Formal interface assertions

Architecture (Xia) owns the assertions. Path convention:

```
formal/<iface>/*.sv
formal/<iface>/*.sby
```

Each `<iface>` directory is self-contained: SystemVerilog assertions plus a
small stub so SymbiYosys can run the job **without product RTL**.

The gate (`scripts/gate/formal.sh`) walks `formal/*/*.sby` and runs
`sby -f` on each file. Any failure fails the job. When no `.sby` files
exist the job succeeds and prints `no assertions yet`.

## `formal/cmn/` — `ub_cmn_mem_1r1w`

CODING_STYLE §10 / PR #20 (Xia timing proposal). Yosys-compatible clocked
`assert`/`cover`. Not product RTL.

| File | Role |
| --- | --- |
| `ub_cmn_mem_1r1w_if_props.sv` | Bindable properties. `anyconst` address; written bit + data for that address only. `ASSERT_NO_UNINIT_READ` (default 1). |
| `ub_cmn_mem_1r1w_formal_ref.sv` | Formal-only synthesizable behavioral 1R1W. Design-B adds the pycc leaf. |
| `ub_cmn_mem_1r1w_harness.sv` | Env assumes (in-range; no uninit read of the watched address) so BMC converges. |
| `cmn.sby` | BMC + cover (d5w8) and `bmc_m16` / `cover_m16` (d64w64m16) |

`make -C formal` still runs every `formal/<iface>/<iface>.sby`. The CI job
is `scripts/gate/formal.sh`.
