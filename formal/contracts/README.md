# formal/contracts — NW↔TP and TP↔TA (轨道 B)

Harness-driven SVA. No product RTL (GATE-FOR-001). Signal names follow
`docs/arch/LAYER_CONTRACTS.md` §2 / §3.

| File | Role |
| --- | --- |
| `nw_tp.sby` / `tp_ta.sby` | Default tasks `cover` / `bmc` / `prove`. Assert + cover only. |
| `nw_tp_assume_diag.sby` / `tp_ta_assume_diag.sby` | Named diagnostic task `assume_diag`. The only tasks that read `*_assume.sv`. |

`GATE-PRIVATE-PARENT-FREE` (`docs/rules/verif_gate.md` §11): contract
`assume` is not in default `bmc`/`cover`/`prove` and not in an unprefixed
shared file of those tasks.

`GATE-FORMAL-DEPTH` §5 rule 3: BMC depth ≥ deepest reachable cover step + 6.
Planned deepest cover ≤ 16, so BMC is 22 until a run measures otherwise.
