#!/usr/bin/env python3
"""Bit-exact: pyCircuit mapping vs tb/models UbPcsLaneDist (one PMA-word block)."""

from __future__ import annotations

import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tb.models.ub_pcs_lane_dist import (  # noqa: E402
    UbPcsLaneDist,
    UbPcsLaneDistConfig,
    pack_pma_word,
)


def leaf_map(data_in: int, num_lanes: int, pma_w: int = 32, sym_w: int = 8) -> int:
    """Same mapping as spike/pycircuit_toolchain/ub_pcs_lane_dist.py."""
    nsym = num_lanes * (pma_w // sym_w)
    mask = (1 << sym_w) - 1
    ca = [(data_in >> (k * sym_w)) & mask for k in range(nsym)]
    out = 0
    for j in range(num_lanes):
        for i in range(pma_w // sym_w):
            src = (nsym - 1) - i * num_lanes - j
            out |= ca[src] << (j * pma_w + i * sym_w)
    return out


def model_map(data_in: int, num_lanes: int, pma_w: int = 32, sym_w: int = 8) -> int:
    nsym = num_lanes * (pma_w // sym_w)
    mask = (1 << sym_w) - 1
    ca = [(data_in >> (k * sym_w)) & mask for k in range(nsym)]
    cfg = UbPcsLaneDistConfig(n_symbols=nsym, pma_w=pma_w, symbol_bits=sym_w)
    lanes = UbPcsLaneDist(num_lanes, cfg).distribute(ca)
    words = [pack_pma_word(lane, pma_w, sym_w) for lane in lanes]
    out = 0
    for j, w in enumerate(words):
        out |= w << (j * pma_w)
    return out


def pr_ref_map(data_in: int, num_lanes: int, pma_w: int = 32, sym_w: int = 8) -> int:
    """Mapping of origin/cursor/rtl-m1-leaf-batch1-e5bb (forward stripe)."""
    nsym = num_lanes * (pma_w // sym_w)
    mask = (1 << sym_w) - 1
    out = 0
    for s in range(nsym):
        lane = s % num_lanes
        pos = s // num_lanes
        sym = (data_in >> (s * sym_w)) & mask
        out |= sym << (lane * pma_w + pos * sym_w)
    return out


def main() -> int:
    rng = random.Random(0)
    for n in (4, 8):
        width = n * 32
        for _ in range(64):
            din = rng.getrandbits(width)
            leaf = leaf_map(din, n)
            model = model_map(din, n)
            pref = pr_ref_map(din, n)
            if leaf != model:
                print(f"FAIL model N={n} din=0x{din:x} leaf=0x{leaf:x} model=0x{model:x}")
                return 1
        # Deterministic first-symbols check matching test_codec1_x4_first_symbols.
        ca = list(range(n * 4))
        din = 0
        for k, s in enumerate(ca):
            din |= s << (k * 8)
        leaf = leaf_map(din, n)
        assert leaf == model_map(din, n)
        lane0_lsb = leaf & 0xFF
        expect = ca[(n * 4 - 1) - 0]
        if lane0_lsb != expect:
            print(f"FAIL Lane<0,0> N={n} got {lane0_lsb} expect {expect}")
            return 1
        match_pr = all(
            leaf_map(rng.getrandbits(width), n) == pr_ref_map(rng.getrandbits(width), n)
            for _ in range(8)
        )
        # Use a shared din for the PR compare printout.
        sample = 0x0123456789ABCDEF
        sample &= (1 << width) - 1
        same_pr = leaf_map(sample, n) == pr_ref_map(sample, n)
        print(
            f"PASS N={n}: leaf==tb.models UbPcsLaneDist "
            f"(n_symbols={n*4}, 64 random + identity CA); "
            f"vs PR e5bb sample match={same_pr}"
        )
        _ = match_pr
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
