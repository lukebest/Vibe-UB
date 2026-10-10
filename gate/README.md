# Gate lists (tool gatekeeper)

Machine-readable lists the CI scripts honor. Rules:
[docs/rules/verif_gate.md](../docs/rules/verif_gate.md).

| File | Purpose |
| --- | --- |
| `legacy.txt` | D10 leftover RTL — report-only until a migration PR |
| `handwritten.yml` | Approved handwritten SV (today: `ub_rst_sync.sv` only) |
| `stubs.yml` | Approved behavioral stubs / blackboxes (C-line SRAM) |
| `hooks_ports.yml` | Per-module extra HOOKS ports (SPEC §10 / §11 (f)) |

Approval: same as `waivers/`. YAML entries need a verification gatekeeper
in `approver`. CODEOWNERS routes `/gate/` to `lukebest`.

Runnable jobs live in `scripts/gate/` (`make gate`).
