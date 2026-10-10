# Gate lists moved

Machine-readable lists now live next to the scripts:

- [`scripts/gate/legacy.txt`](../scripts/gate/legacy.txt)
- [`scripts/gate/handwritten.yml`](../scripts/gate/handwritten.yml)
- [`scripts/gate/blackbox.yml`](../scripts/gate/blackbox.yml) (`kind`: `stub` | `macro`)
- [`scripts/gate/hooks_ports.yml`](../scripts/gate/hooks_ports.yml)
- [`scripts/gate/pycircuit_migrate.txt`](../scripts/gate/pycircuit_migrate.txt)

Rules: [docs/rules/verif_gate.md](../docs/rules/verif_gate.md).
Approval: same as `waivers/`. CODEOWNERS covers `/scripts/gate/*.yml` and `*.txt`.

Xia: `ub_cmn_mem_1r1w` is a normal pycc leaf (`pycircuit/cmn/` → `rtl/cmn/`), not a blackbox.
