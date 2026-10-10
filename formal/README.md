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
