"""Lane window helpers. Goldens come only from tb.vibe_uvm.golden."""

from __future__ import annotations

from tb.vibe_uvm.golden import lane_dist as LD

PMA_W = 32
SYM_W = 8
RS_N = 128


def nsym(num_lanes: int) -> int:
    return num_lanes * (PMA_W // SYM_W)


def pack_symbols(symbols: list[int]) -> int:
    word = 0
    for i, s in enumerate(symbols):
        word |= (s & 0xFF) << (i * SYM_W)
    return word


def unpack_lane_first_symbols(data_out: int, num_lanes: int) -> list[int]:
    return [(data_out >> (j * PMA_W)) & 0xFF for j in range(num_lanes)]


def expected_window(symbols: list[int], num_lanes: int) -> int:
    cfg = LD.UbPcsLaneDistConfig(n_symbols=len(symbols))
    model = LD.UbPcsLaneDist(num_lanes, cfg)
    lanes = model.distribute(symbols)
    words = model.pack_lane_words(lanes)
    out = 0
    for j, lw in enumerate(words):
        out |= lw[0] << (j * PMA_W)
    return out


def expected_dedist(striped: int, num_lanes: int) -> int:
    width = num_lanes * PMA_W
    ns = nsym(num_lanes)
    lanes_syms: list[list[int]] = []
    for j in range(num_lanes):
        word = (striped >> (j * PMA_W)) & ((1 << PMA_W) - 1)
        lanes_syms.append(LD.unpack_pma_word(word, PMA_W, SYM_W))
    # One PMA word per lane → ns symbols total.
    cfg = LD.UbPcsLaneDistConfig(n_symbols=ns)
    model = LD.UbPcsLaneDist(num_lanes, cfg)
    ca, _ = model.recover(lanes_syms)
    return pack_symbols(ca) & ((1 << width) - 1)


def walking_ones(width: int):
    for bit in range(width):
        yield 1 << bit


def rs128_high_windows(num_lanes: int = 4) -> list[tuple[list[int], int]]:
    """Parent presents high-end windows first (PR #5 module note / UB-PHY §3.2.2.3)."""
    win = nsym(num_lanes)
    ca = list(range(RS_N))
    model = LD.UbPcsLaneDist(num_lanes)
    packed = model.pack_lane_words(model.distribute(ca))
    nwords = RS_N // win
    rows = []
    for k in range(nwords):
        window = ca[RS_N - win * (k + 1) : RS_N - win * k]
        exp = 0
        for j in range(num_lanes):
            exp |= packed[j][k] << (j * PMA_W)
        rows.append((window, exp))
    return rows
