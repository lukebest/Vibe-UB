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

322/323 `RETRY_WAIT_CYC` / `PROBE_WAIT_CYC` covers live in `formal/dll/`
(LAYER_CONTRACTS §3: DLL §4.7.3.3 / LMSM §3.4.3.2).
TP `nw_tp` keeps only `c_rto` and `c_ack_coal` (§6.4.2.1).

Measured (`sby` + Yosys 0.33 / z3; harness-driven, no assume):

| sby | 任务 | 最深 cover 步 | BMC depth | 余量 |
| --- | --- | ---: | ---: | ---: |
| `nw_tp.sby` | cover | 14 (`c_ack_coal`, `c_psn_wrap`) | — | — |
| `nw_tp.sby` | bmc / prove | — | 22 | 22 ≥ 14+6 |
| `nw_tp_assume_diag.sby` | assume_diag | （无 cover 任务） | 22 | — |
| `tp_ta.sby` | cover | 16 (`c_cmp_fail`) | — | — |
| `tp_ta.sby` | bmc / prove | — | 22 | 22 ≥ 16+6 |
| `tp_ta_assume_diag.sby` | assume_diag | （无 cover 任务） | 22 | — |

`nw_tp` cover 步：sop_eop 3、hold 5、two_beat 7、rx 9、drop 10、link_down 11、icrc_cfg7 12、rto 13、ack_coal/psn_wrap 14。
`tp_ta` cover 步：submit_byp 3、payload 4、done/msn 5、op_hold 6、fail 8、deliver 9、deliver_data 10、flush_empty 12、cmp_ok/full_cfg 14、cmp_fail 16。
