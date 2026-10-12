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

B-line contract asserts live in `formal/contracts/` (NW↔TP, TP↔TA).
Default `cover`/`bmc`/`prove` tasks do not include contract `assume`;
that file is only read by the named `assume_diag` sby (see
`docs/rules/verif_gate.md` GATE-PRIVATE-PARENT-FREE and GATE-FORMAL-DEPTH
§5 rule 3).
