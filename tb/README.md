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
    scrambler.py            UB-PHY §3.2.2.4 / §3.2.3.2 / §3.2.6
    lane_dist.py            UB-PHY §3.2.2.3 / §3.2.5
    bcrc.py                 UB-DL §4.3.2.2.4 / §4.7.2
    config.py               pending knobs
    tests/                  pytest
  vibe_uvm/                 uvm-python skeleton (named so it does not shadow the `uvm` package)
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

| Model | Spec | SPEC | What is closed vs pending |
| --- | --- | --- | --- |
| `LaneScrambler` | UB-PHY §3.2.2.4, §3.2.3.2, §3.2.6 | §2.4 | 8-bit symbols; LSB first; AMCTL/EEIB exempt; LTB/DLL scrambled; per-lane; EDF/SDF reset rules. Poly/seeds/LFSR drawing: pending (see below). |
| `LaneDist` | UB-PHY §3.2.2.3, §3.2.5 | §2.4, §9 | 8-bit symbols; x1/x4/x8; CodecNum 1 formula + CodecNum 2. `FEC_CODEC_NUM` 待定 (default 1). |
| `Bcrc` | UB-DL §4.3.2.2.4, §4.7.2 | §2.6, §7 | CRC30 poly, init all-1s, Bit7-first, no invert, 32-bit {Reserved, ERROR_FLAG, CRC30}. Info-bit coverage / byte packing: pending confirm. |

No official numeric vector tables appear in those sections. Tests are invertibility, the §3.2.2.3 index formula, and BCRC detect/attach properties.

## Pending parameters (do not treat as closed)

See `models/config.py` and SPEC §13.

1. Scrambler LFSR taps — §3.2.2.4 silent; default PRBS23 `x^23+x^18+1` from §3.2.6.
2. Per-lane seed table — §3.2.2.4 says seeds follow AMCTL.LID; no table written.
3. Fibonacci vs Galois, which bit is XOR'd with data.
4. Whether exempt symbols advance the LFSR (default: no; §3.2.3.2 "not input").
5. `FEC_CODEC_NUM` (SPEC §9 / §13.2, suggest 1).
6. Whether Reserved/ERROR_FLAG enter CRC30 (default yes: "before the CRC30 field", §4.7.2).
7. BCRC byte packing in the 160-bit flit (default: byte 16 is the high byte of the 32-bit word).
8. All other SPEC §13 items (RX buffer, AMCTL/data pin share, `MAX_DP_FLITS`, scale encodings, …) — not modelled here.

## SPEC gaps / tensions seen while writing models

- UB-PHY §3.2.2.4 states additive per-lane scrambling and seed reset rules but does not write the polynomial or seed table. §3.2.6 is the only place that names PRBS23 as "the same as scrambling's".
- UB-PHY §3.2.2.3 gives a complete index formula (used as the known vector). Figures 3-5 / 3-6 are not copied.
- UB-DL §4.7.2 writes the CRC30 polynomial and bit-order rule but has no numeric example. Figure 4-39 is not in the public tree.
- SPEC §3.1 RX is valid-only (no `pma_rx_ready` / `pcs2dll_ready`); NW RX stays valid/ready. The valid-only agent is for the PMA/PCS-DLL RX path.
- SPEC §12: existing `rtl/` lane dist is 2-bit and the scrambler is 58-bit. Models follow the spec, not that RTL.
- VERIF_PLAN (PR #3) still says hook/register section numbers were "待 SPEC"; they are now SPEC §10 / REGMAP §2.4.

Git history of this repo will be rewritten; rebase this stack when that happens.
