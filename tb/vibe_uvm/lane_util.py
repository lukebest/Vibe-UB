"""Lane window helpers.

Goldens: ``tb.vibe_uvm.golden`` (model/ then tb/models) AND a second
implementation of the SPEC §2.3 / §2.4 formula written here. The two must
agree. Never derive the expected word from DUT output.
"""

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


def unpack_symbols(word: int, num_lanes: int) -> list[int]:
    return [(word >> (i * SYM_W)) & 0xFF for i in range(nsym(num_lanes))]


def unpack_lane_first_symbols(data_out: int, num_lanes: int) -> list[int]:
    return [(data_out >> (j * PMA_W)) & 0xFF for j in range(num_lanes)]


def spec_src(i: int, j: int, num_lanes: int) -> int:
    """UB-PHY §3.2.2.3 / SPEC §2.3 §2.4: Lane<j,i> = CA<(NSYM-1)-i*N-j>."""
    return (nsym(num_lanes) - 1) - i * num_lanes - j


def forward_src(i: int, j: int, num_lanes: int) -> int:
    """Wrong map attributed to #5: Lane<j,i> = CA<i*N+j>."""
    return i * num_lanes + j


def _stripe(symbols: list[int], num_lanes: int, src_fn) -> int:
    ns = nsym(num_lanes)
    if len(symbols) != ns:
        raise ValueError(f"need {ns} symbols, got {len(symbols)}")
    spl = PMA_W // SYM_W
    out = 0
    for i in range(spl):
        for j in range(num_lanes):
            src = src_fn(i, j, num_lanes)
            out |= (symbols[src] & 0xFF) << (j * PMA_W + i * SYM_W)
    return out


def spec_dist_word(symbols: list[int], num_lanes: int) -> int:
    return _stripe(symbols, num_lanes, spec_src)


def forward_dist_word(symbols: list[int], num_lanes: int) -> int:
    return _stripe(symbols, num_lanes, forward_src)


def spec_dedist_word(striped: int, num_lanes: int) -> int:
    ns = nsym(num_lanes)
    spl = PMA_W // SYM_W
    symbols = [0] * ns
    for i in range(spl):
        for j in range(num_lanes):
            src = spec_src(i, j, num_lanes)
            symbols[src] = (striped >> (j * PMA_W + i * SYM_W)) & 0xFF
    return pack_symbols(symbols)


def _model_dist_word(symbols: list[int], num_lanes: int) -> int:
    cfg = LD.UbPcsLaneDistConfig(n_symbols=len(symbols))
    model = LD.UbPcsLaneDist(num_lanes, cfg)
    lanes = model.distribute(symbols)
    words = model.pack_lane_words(lanes)
    out = 0
    for j, lw in enumerate(words):
        out |= lw[0] << (j * PMA_W)
    return out


def _model_dedist_word(striped: int, num_lanes: int) -> int:
    width = num_lanes * PMA_W
    ns = nsym(num_lanes)
    lanes_syms: list[list[int]] = []
    for j in range(num_lanes):
        word = (striped >> (j * PMA_W)) & ((1 << PMA_W) - 1)
        lanes_syms.append(LD.unpack_pma_word(word, PMA_W, SYM_W))
    cfg = LD.UbPcsLaneDistConfig(n_symbols=ns)
    model = LD.UbPcsLaneDist(num_lanes, cfg)
    ca, _ = model.recover(lanes_syms)
    return pack_symbols(ca) & ((1 << width) - 1)


def _lock_goldens(spec: int, model: int, symbols: list[int], num_lanes: int) -> int:
    if spec != model:
        raise AssertionError(
            f"golden split: SPEC formula 0x{spec:x} vs tb/models 0x{model:x}"
        )
    fwd = forward_dist_word(symbols, num_lanes)
    if spec == fwd and len(set(symbols)) > 1:
        raise AssertionError("SPEC formula collapsed onto Lane<j,i>=CA<i*N+j>")
    return spec


def expected_window(symbols: list[int], num_lanes: int) -> int:
    spec = spec_dist_word(symbols, num_lanes)
    model = _model_dist_word(symbols, num_lanes)
    return _lock_goldens(spec, model, symbols, num_lanes)


def expected_dedist(striped: int, num_lanes: int) -> int:
    spec = spec_dedist_word(striped, num_lanes)
    model = _model_dedist_word(striped, num_lanes)
    if spec != model:
        raise AssertionError(
            f"dedist golden split: SPEC 0x{spec:x} vs model 0x{model:x}"
        )
    return spec


def first_mismatch(got: int, exp: int, num_lanes: int) -> dict | None:
    xor = got ^ exp
    if xor == 0:
        return None
    for lane in range(num_lanes):
        for bit in range(PMA_W):
            pos = lane * PMA_W + bit
            if (xor >> pos) & 1:
                return {
                    "lane": lane,
                    "bit": bit,
                    "i": bit // SYM_W,
                    "exp_bit": (exp >> pos) & 1,
                    "got_bit": (got >> pos) & 1,
                    "exp": exp,
                    "got": got,
                }
    return None


def mismatch_msg(got: int, exp: int, num_lanes: int, ctx: str = "") -> str:
    hit = first_mismatch(got, exp, num_lanes)
    if hit is None:
        return f"{ctx} match".strip()
    return (
        f"{ctx} first mismatch lane={hit['lane']} bit={hit['bit']} "
        f"(PMA symbol i={hit['i']}): expected {hit['exp_bit']} got {hit['got_bit']}; "
        f"word exp=0x{hit['exp']:x} got=0x{hit['got']:x}"
    ).strip()


def compare_word(got: int, exp: int, num_lanes: int, ctx: str) -> None:
    if got != exp:
        raise AssertionError(mismatch_msg(got, exp, num_lanes, ctx))


def walking_ones(width: int):
    for bit in range(width):
        yield 1 << bit


def incrementing_symbols(num_lanes: int) -> list[int]:
    return list(range(nsym(num_lanes)))


def onehot_symbols(num_lanes: int):
    """Each symbol 0x01 in one position; locks mapping direction."""
    ns = nsym(num_lanes)
    for idx in range(ns):
        row = [0] * ns
        row[idx] = 0x01
        yield idx, row


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
        # Window-level SPEC formula must match the full-codeword slice.
        compare_word(exp, spec_dist_word(window, num_lanes), num_lanes, f"rs128 k={k}")
        rows.append((window, exp))
    return rows
