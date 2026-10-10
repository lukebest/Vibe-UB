# Local STEP 1 pre-check (non-gating)

These SPEC-formula references are a **local pre-check only**. They are
**not** the merge gate.

Gating references live under `formal/<layer>/ref/` and are driven by
`equiv_ref.sh` (verification, PR #16). This directory must not grow a
`formal/` tree.

Use:

```bash
bash scripts/precheck/run.sh
```

What is here:

| File | Role |
| --- | --- |
| `ub_pyc_rst_adapt_spec.v` | SPEC §4.2 polarity (`rst_pyc = ~rst_n_sync`) |
| `ub_pcs_lane_dist_spec.v` / `ub_pcs_lane_dedist_spec.v` | UB-PHY §3.2.2.3 reverse-stripe |
| `ub_dll_bcrc_spec.v` / `ub_dll_bcrc_check_spec.v` | bit-serial CRC30 (SPEC §2.6) |
| `ub_dll_bcrc_next_spec.v` | combinational next-state of that CRC |
| `tb_bcrc_cosim.v` | directed + random RTL vs bit-serial spec |
| `emit_bcrc_next.py` | combo-only pycc netlist for the next-state check |
