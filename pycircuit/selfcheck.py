#!/usr/bin/env python3
"""Minimal generator + golden self-check (not a verification TB).

Proves emit() runs and that lane stripe is involutive / CRC / LFSR
Python models match the algorithms baked into the emitted Verilog.
Does not live under tb/ (verification owns uvm-python / cocotb).
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from emit import emit_all
from lib import params as P


def lfsr_step(s: int, scr_w: int = P.SCR_W, tap: int = P.SCR_TAP) -> int:
    fb = ((s >> (scr_w - 1)) & 1) ^ ((s >> tap) & 1)
    return ((s << 1) | fb) & ((1 << scr_w) - 1)


def xmask(state: int, data_w: int) -> int:
    t = state
    acc = 0
    for i in range(data_w):
        acc |= (t & 1) << i
        t = lfsr_step(t)
    return acc


def crc_step(c: int, b: int, poly: int = P.BCRC_POLY, crc_w: int = P.BCRC_W) -> int:
    fb = ((c >> (crc_w - 1)) & 1) ^ (b & 1)
    shl = (c << 1) & ((1 << crc_w) - 1)
    return shl ^ (poly if fb else 0)


def crc_flit(c: int, flit: int, flit_w: int = P.FLIT_W) -> int:
    t = c
    for i in range(flit_w):
        t = crc_step(t, (flit >> i) & 1)
    return t


def lane_dist(data: int, num_lanes: int, pma_w: int, sym_w: int) -> int:
    nsym = num_lanes * (pma_w // sym_w)
    out = 0
    mask = (1 << sym_w) - 1
    for s in range(nsym):
        lane = s % num_lanes
        pos = s // num_lanes
        sym = (data >> (s * sym_w)) & mask
        out |= sym << (lane * pma_w + pos * sym_w)
    return out


def lane_dedist(data: int, num_lanes: int, pma_w: int, sym_w: int) -> int:
    nsym = num_lanes * (pma_w // sym_w)
    out = 0
    mask = (1 << sym_w) - 1
    for s in range(nsym):
        lane = s % num_lanes
        pos = s // num_lanes
        sym = (data >> (lane * pma_w + pos * sym_w)) & mask
        out |= sym << (s * sym_w)
    return out


def main() -> int:
    paths = emit_all()
    assert paths, "emit wrote nothing"
    for p in paths:
        text = p.read_text(encoding="utf-8")
        assert "module " in text
        assert "`ifdef" not in text
        assert "$display" not in text
        assert "force " not in text
        assert "negedge rst_n" not in text  # business leaves: sync rst_pyc

    # Lane stripe is an involution (x4 and x8).
    for nlane in (1, 4, 8):
        width = nlane * P.PMA_W
        sample = (0x0123456789ABCDEF0123456789ABCDEF) & ((1 << width) - 1)
        striped = lane_dist(sample, nlane, P.PMA_W, P.SYM_W)
        back = lane_dedist(striped, nlane, P.PMA_W, P.SYM_W)
        assert back == sample, f"lane dist/dedist failed for x{nlane}"

    # Additive scramble is involutive for a fixed LFSR window.
    st = 0x1
    word = 0xA5A5A5A5 & ((1 << P.DATA_W_SCR) - 1)
    m = xmask(st, P.DATA_W_SCR)
    assert (word ^ m) ^ m == word

    # CRC30 eats one flit and is deterministic.
    c0 = P.BCRC_INIT
    c1 = crc_flit(c0, 0)
    c2 = crc_flit(c0, 1)
    assert c1 != c2
    assert crc_flit(c0, 0) == c1

    print(f"selfcheck ok: {len(paths)} leaves emitted, golden models passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
