# `model/` — architecture-owned Python reference

| Item | Value |
| --- | --- |
| Owner | Architecture (Xia). See [docs/TEAM.md](../docs/TEAM.md) §2 |
| Role | RTL-independent golden answer shared by design and verification |
| Normative sources | [docs/SPEC.md](../docs/SPEC.md), [docs/REGMAP.md](../docs/REGMAP.md); UB-PHY / UB-DL **section numbers only** |
| Not in this package | `model/regs.py` (generated from REGMAP YAML by a separate PR) |

This package is the home of the M1 golden models. Product RTL (`rtl/`) and
the uvm-python TB (`tb/`) consume it; they do not own it.

## Rules

1. **SPEC section-by-section.** Each module docstring cites the SPEC / UB-PHY /
   UB-DL sections it implements. Behaviour that is not in those sections stays
   out of the model, or is marked SPEC §13 (required argument, no default).
2. **No RTL dependency.** `model/` is pure Python. It must not import
   cocotb, uvm-python, pyCircuit, or anything under `rtl/`. It must not read
   Verilog, netlists, or hierarchical paths.
3. **Do not copy UB Base Spec text.** Cite section numbers only. Project-written
   `docs/SPEC.md` wording may be restated; official tables/figures must not
   appear here.
4. **Open knobs stay required.** Scrambler `poly_taps` and `lid_to_seed` have
   **no defaults** (SPEC §13). Tests pass 示例 values, not project defaults.

## Layout

| Path | What |
| --- | --- |
| `ub_pcs_lane_dist.py` | 8-bit symbol distribution / collection (UB-PHY §3.2.2.3, §3.2.5; SPEC §2.4, §3.3) |
| `ub_pcs_scrambler.py` | Per-lane additive PRBS23 (UB-PHY §3.2.2.4, §3.2.3.2, §3.2.6; SPEC §2.4) |
| `ub_dll_bcrc.py` | CRC30 BCRC (UB-DL §4.3.2.2.4, §4.7.2; SPEC §2.6) |
| `config.py` | Remaining SPEC §13 knobs (`FEC_CODEC_NUM` default 1 for the lane formula only) |
| `tests/` | Package unit tests, including an independent bit-by-bit BCRC cross-check |
| `regs.py` | **Not authored here.** Generated register model (other PR) |

`tb/models/` is a thin re-export shim so existing `from tb.models…` imports
and `tb/models/tests` keep working.

## How verification scoreboards call it

The uvm-python scoreboard ([`tb/vibe_uvm/scoreboard.py`](../tb/vibe_uvm/scoreboard.py))
compares monitor transactions to a Python expected value. Import the golden
from this package (or the shim) and feed the same stimulus the DUT saw:

```python
from model import UbDllBcrc, UbPcsLaneDist, UbPcsScrambler, UbPcsScramblerConfig

# BCRC: attach the 32-bit word, then compare the last flit / CRC30 only.
exp_flits = UbDllBcrc().attach(list(tx_flits), error_flag=0)
scoreboard.compare(exp_flits[-1], dut_last_flit, "bcrc.attach")

# Lane dist: 8-bit symbols, recover must invert distribute.
lanes = UbPcsLaneDist(lane_num=4).distribute(codeword_a)
scoreboard.compare(lanes, mon_lanes, "lane_dist")

# Scrambler: taps and LID→seed are REQUIRED (SPEC §13). Pass the same
# 示例 / future-closed map the TB agreed with architecture; never invent a
# product default inside the model.
cfg = UbPcsScramblerConfig(poly_taps=taps, lid_to_seed=lid_map)
tx = UbPcsScrambler(cfg, amctl_lid=lid)
scoreboard.compare(tx.process_word(plain, en=True), dut_word, "scrambler")
```

`ScoreboardBase.compare(expected, actual, ctx)` is the hook. Do not force DUT
internals (D13); drive ports / SPEC §10 hooks and compare against this package.

Unit tests: `python3 -m pytest model/tests tb/models/tests` (from repo root,
`PYTHONPATH=.`) or `make -C tb pytest`.
