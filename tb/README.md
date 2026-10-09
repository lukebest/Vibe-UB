# Vibe-UB testbench (uvm-python)

Official TB for M1. Framework is **only** uvm-python on cocotb 1.9.x (D7).
Pins live in [`../TOOLCHAIN.lock`](../TOOLCHAIN.lock) and [`requirements.txt`](requirements.txt).

Handwritten Verilog under `tb/pcs/` and `tb/dll/` is leftover (D10 → `legacy/` later).
It is **not** the official regression.

## Layout

```
tb/
  README.md                 this file
  requirements.txt          exact Python pins
  Makefile                  dual-netlist entry (TEST_HOOKS=0 and 1)
  pytest.ini                golden-model unit tests
  models/                   Python golden (no RTL)
    ub_pcs_scrambler.py     interface only — pending SPEC (UB-PHY §3.2.2.4)
    ub_pcs_lane_dist.py     UB-PHY §3.2.2.3 / §3.2.5 / SPEC §3.3
    ub_dll_bcrc.py          interface only — pending SPEC (UB-DL §4.3.2.2.4)
    config.py               closed widths + pending knobs
    tests/                  pytest (scrambler/BCRC compute skipped)
  vibe_uvm/                 uvm-python skeleton (named so it does not shadow the `uvm` package)
    ub_csr_map.py           REGMAP offsets (CNT_CLR 0x0224, APPD 0x1E00/0x1F00)
    clk_rst.py              core_clk ≈ 80.57 MHz; rst_n async assert / sync deassert
    seed_log.py             prints `SEED <n>` (D8)
    items.py                randomize() via cocotb-coverage crv
    agents/valid_ready.py   SPEC §3.1
    agents/valid_only.py    SPEC §3.1 (PMA→PCS / PCS→DLL RX)
    agents/csr.py           SPEC §3.2.3
    agents/hook.py          SPEC §10 only; no extra ports
    scoreboard.py           golden compare base
    coverage.py             CoverPoint / CoverCross + JSON export
    env.py                  ub_env
  harness/                  TB-only SV. Not product RTL. Not under rtl/
  tests/tb_selfcheck.py     Icarus / Verilator skeleton TC
  scripts/                  self-check, coverage, TP rollup
  reports/                  regress / cov_func / cov_line
```

## Hard rules

- No SV-UVM, no pyvsc, no unstructured bare cocotb tests (D7 / D8).
- TB never `force` / `deposit` internals (D13). Stimulus is ports or SPEC §10 hooks.
- Product `TEST_HOOKS` is expanded in Python (SPEC §11), not `` `ifdef `` in generated RTL.
- Do not copy 640-bit / PRBS31 width assumptions from Vibe-UB-Switch.

## Clock and reset

- `core_clk` period 12.410 ns ≈ 80.57 MHz (`2.578125 Gbit/s / 32`, SPEC §4.1).
- `rst_n` low: async assert, sync deassert (SPEC §4.2).

## Dual netlist entry

```bash
python3 -m venv venv && . venv/bin/activate
pip install -r tb/requirements.txt
make -C tb models
make -C tb selfcheck-both SIM=icarus          # pass/fail gate (D7)
make -C tb selfcheck-both SIM=verilator       # compare + optional LINE_COV=1
# or
tb/scripts/run_selfcheck.sh
```

`TEST_HOOKS=0` compiles `harness/tb_passthru_hooks0.sv` (no `tb_*` ports).
`TEST_HOOKS=1` compiles `harness/tb_passthru_hooks1.sv` (SPEC §10 bundle).

## Coverage scaffold

| Kind | Where | Notes |
| --- | --- | --- |
| Functional | `reports/cov_func/*.json` (+ yaml if the helper works) | CoverPoint / CoverCross (D8) |
| Line | `reports/cov_line/` via `make -C tb cov-line` | Verilator `--coverage`; denominator = HOOKS (SPEC §11) |
| TP rollup | `reports/regress/summary.txt` | `scripts/summarize_tp.py` |

Icarus does not produce line coverage.

## Golden models

| Model | Spec | SPEC | Status |
| --- | --- | --- | --- |
| `UbPcsScrambler` | UB-PHY §3.2.2.4, §3.2.3.2 | §2.4 | **Interface only.** Core step raises `NotImplementedError("pending SPEC")`. Known: seed = `AMCTL.LID` (not phys / LTB.Lane_ID); LSB first. No poly / init / invert / `DATA_W` default. 1-cycle valid-only leaf (PR #5 ports, wiring only). |
| `UbPcsLaneDist` | UB-PHY §3.2.2.3, §3.2.5, §3.4.1 | §2.4, §3.3, §9 | **Implemented.** 8-bit symbols; x1/x4/x8; CodecNum 1/2 formula; symbol 0 first; PMA word symbol 0 at LSB; 0-cycle. |
| `UbDllBcrc` | UB-DL §4.3.2.2.4, §4.7.2 | §2.6 | **Interface only.** Compute raises `NotImplementedError("pending SPEC")`. Known packing: `{rsvd, ERROR_FLAG, CRC30[29:0]}`. No poly / init / invert default. 1-cycle valid-only leaf (PR #5 ports, wiring only). |

No LMB/LTB golden in this PR. LTB/CLTB field ports are SPEC §3.3.4 / UB-PHY §3.4.1 (`fec_mode_ctrl[2:0]`, `lmsm2pcs_pattern`, per-lane Lane_ID + CRC, latch at next LMB). Names wait for the next PR #4 commit.

Leaf agents use the generic valid-only / valid-ready agents. Port lists on the model modules match SPEC §2.4 / §2.6 (and the PR #5 description for wiring only).

## Pending parameters (do not treat as closed)

See `models/config.py` and SPEC §13.

1. Scrambler polynomial, init, invert, `DATA_W` — pending SPEC. Do not copy PR #5 / Switch.
2. `AMCTL.LID` → seed map (seed *source* is known).
3. BCRC polynomial, init, invert, bit-order of the step — pending SPEC. Packing is known.
4. `FEC_CODEC_NUM` (SPEC §9 / §13.2, suggest 1).
5. All other SPEC §13 items — not modelled here.

## SPEC gaps / tensions seen while writing models

- UB-PHY §3.2.2.4 states additive per-lane scrambling and seed reset rules but does not write the polynomial or seed table.
- UB-PHY §3.2.2.3 gives a complete index formula (used as the known vector for lane dist).
- SPEC §3.1 RX is valid-only (no `pma_rx_ready` / `pcs2dll_ready`); NW RX stays valid/ready.
- SPEC §12: existing `rtl/` lane dist is 2-bit and the scrambler is 58-bit. Models follow the spec, not that RTL.
- VERIF_PLAN (PR #3) still says hook/register section numbers were "待 SPEC"; they are now SPEC §10 / REGMAP §2.4.

Git history of this repo will be rewritten; rebase this stack when that happens.
