# Waivers

Machine-readable exemption list for the tool gate. Rules and fail criteria:
[docs/rules/verif_gate.md](../docs/rules/verif_gate.md). Ownership: tool
gatekeeper (verification lead, [TEAM.md](../docs/TEAM.md) §4).

## Files

| File | Check |
| --- | --- |
| `lint.yml` | Verilator `--lint-only -Wall` |
| `synth.yml` | Yosys latch / multi-drive / combo-loop |
| `cdc.yml` | Structural CDC / RDC |
| `approvers.yml` | Gatekeeper logins (verification only) |
| `pending/` | Drafts marked 待守门人批准 — **not** loaded |

D10 leftover RTL is **not** waived here. It is listed in
`gate/legacy.txt` and is report-only until a legacy-migration PR
removes the path and the gatekeeper approves that list change.

Handwritten SV, stubs/blackboxes, and HOOKS extra ports are listed under
`gate/` with the same approver rules as this directory.

## Required fields

| Field | Meaning |
| --- | --- |
| `id` | Stable name (`WAIVER_*`) |
| `check` | `lint` / `synth` / `cdc` |
| `module` | Module name (`*` allowed) |
| `file` | Path or glob |
| `rule` | Tool rule or gate rule id |
| `message` | Regex matched against the tool message (optional) |
| `reason` | Why the check cannot be fixed in RTL |
| `approver` | Must be a login in `approvers.yml` (verification) |
| `approved_date` | ISO date of written approval |
| `review_when` | Expiry date or revisit condition |

Scripts load only entries whose `approver` is a gatekeeper and whose
`status` is not `draft` / `pending` / `todo`. Empty or `TODO` approver
fields are printed and ignored.

CODEOWNERS routes reviews of this directory to `lukebest`.
