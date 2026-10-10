"""Directed + random sequences. Seeds are caller-owned (VERIF_PLAN §10.3)."""

from __future__ import annotations

from random import Random

from model.ub_cmn_mem_1r1w import clog2
from tb.cmn.items import MemCycle, all_seg_mask

# DEPTH/WIDTH combos include a non-power-of-two DEPTH (5) as required.
POSITIVE_COMBOS: tuple[tuple[int, int, bool], ...] = (
    (8, 16, True),
    (5, 8, True),
    (5, 9, True),
    (4, 8, True),
    (3, 1, True),
    (8, 16, False),
    (5, 8, False),
)

DEFAULT_SEED = 1

POSITIVE_CASES: tuple[str, ...] = (
    "random",
    "conflict",
    "back2back",
    "boundary",
    "hold",
    "data_onehot",
    "addr_onehot",
    "fill_fwd_rev",
    "data_eq_addr",
)
NEGATIVE_CASES: tuple[str, ...] = ("oor_waddr", "oor_raddr", "uninit", "uninit_conflict")

# DEPTH, WIDTH, WMASK_W, ANUR — NSEG>1 Python self-check combos.
WMASK_COMBOS: tuple[tuple[int, int, int, bool], ...] = (
    (4, 16, 4, True),
    (4, 16, 4, False),
    (8, 16, 4, True),
    (64, 64, 16, True),
)
WMASK_CASES: tuple[str, ...] = (
    "wmask_single",
    "wmask_adjacent",
    "wmask_all",
    "wmask_zero",
    "wmask_conflict",
    "wmask_onehot",
)
WMASK_NEG_CASES: tuple[str, ...] = ("wmask_partial_uninit",)
SMOKE_CASES: tuple[str, ...] = ("random", "wmask_single", "conflict")
SMOKE_RANDOM_N = 8
FULL_WMASK_TAGS = frozenset({"d64w64m16"})
SMOKE_WMASK_TAGS = frozenset({"d512w512m64"})


def addr_bits(depth: int) -> int:
    return max(1, clog2(depth))


def max_addr_encoding(depth: int) -> int:
    return (1 << addr_bits(depth)) - 1


def seq_write_then_read(addr: int, data: int) -> list[MemCycle]:
    return [
        MemCycle(we=1, waddr=addr, wdata=data),
        MemCycle(re=1, raddr=addr),
    ]


def seq_rdata_hold(addr: int = 1, data: int = 0x3C) -> list[MemCycle]:
    return [
        MemCycle(we=1, waddr=addr, wdata=data),
        MemCycle(re=1, raddr=addr),
        MemCycle(),
        MemCycle(we=1, waddr=addr + 1 if addr else 0, wdata=0x11),
    ]


def seq_conflict_read_old(depth: int, width: int) -> list[MemCycle]:
    addr = min(2, depth - 1)
    old = 0x10 & ((1 << width) - 1)
    new = 0x20 & ((1 << width) - 1)
    if old == new:
        old, new = 1, 0
    return [
        MemCycle(we=1, waddr=addr, wdata=old),
        MemCycle(we=1, waddr=addr, wdata=new, re=1, raddr=addr),
        MemCycle(re=1, raddr=addr),
    ]


def seq_back_to_back(depth: int, width: int) -> list[MemCycle]:
    mask = (1 << width) - 1
    n = min(depth, 6)
    cycles: list[MemCycle] = []
    for i in range(n):
        cycles.append(MemCycle(we=1, waddr=i, wdata=(0xA0 + i) & mask))
    # Overlapped write + read of the previous address, then pure reads.
    for i in range(n):
        nxt = (i + 1) % n
        cycles.append(
            MemCycle(
                we=1,
                waddr=nxt,
                wdata=(0x50 + i) & mask,
                re=1,
                raddr=i,
            )
        )
    for i in range(n):
        cycles.append(MemCycle(re=1, raddr=i))
    return cycles


def seq_boundary(depth: int, width: int) -> list[MemCycle]:
    mask = (1 << width) - 1
    last = depth - 1
    return [
        MemCycle(we=1, waddr=0, wdata=mask),
        MemCycle(we=1, waddr=last, wdata=1 & mask, re=1, raddr=0),
        MemCycle(re=1, raddr=last),
        MemCycle(we=1, waddr=0, wdata=2 & mask, re=1, raddr=0),
        MemCycle(we=1, waddr=last, wdata=3 & mask, re=1, raddr=last),
    ]


def seq_random_legal(
    depth: int,
    width: int,
    seed: int,
    n: int = 80,
    *,
    assert_no_uninit_read: bool = True,
    wmask_w: int | None = None,
) -> list[MemCycle]:
    rng = Random(seed)
    if wmask_w is None:
        wmask_w = width
    nseg = width // int(wmask_w)
    written = [0] * depth
    cycles: list[MemCycle] = []
    for _ in range(n):
        item = MemCycle()
        item.randomize_legal(
            rng,
            depth,
            width,
            written,
            assert_no_uninit_read=assert_no_uninit_read,
            wmask_w=wmask_w,
        )
        cycles.append(item)
        if item.we:
            written[item.waddr] |= item.resolved_wmask(nseg)
    return cycles


def _seg_pattern(nseg: int, wmask_w: int, fill: int) -> int:
    sm = (1 << wmask_w) - 1
    word = 0
    val = fill & sm
    for seg in range(nseg):
        word |= val << (seg * wmask_w)
    return word


def _seg_unique(seg: int, wmask_w: int) -> int:
    sm = (1 << wmask_w) - 1
    return ((0x5A + int(seg) * 0x11) & sm) << (int(seg) * wmask_w)


def seq_wmask_single(depth: int, width: int, wmask_w: int) -> list[MemCycle]:
    """Fill, then overwrite one segment; others must hold."""
    nseg = width // wmask_w
    addr = 0
    old = _seg_pattern(nseg, wmask_w, 0x1)
    new = _seg_unique(0, wmask_w) | (old & ~((1 << wmask_w) - 1))
    return [
        MemCycle(we=1, waddr=addr, wdata=old, wmask=all_seg_mask(nseg)),
        MemCycle(re=1, raddr=addr),
        MemCycle(we=1, waddr=addr, wdata=new, wmask=1 << 0),
        MemCycle(re=1, raddr=addr),
    ]


def seq_wmask_adjacent(depth: int, width: int, wmask_w: int) -> list[MemCycle]:
    nseg = width // wmask_w
    addr = min(1, depth - 1)
    old = _seg_pattern(nseg, wmask_w, 0x2)
    new = _seg_unique(0, wmask_w) | _seg_unique(1, wmask_w)
    return [
        MemCycle(we=1, waddr=addr, wdata=old, wmask=all_seg_mask(nseg)),
        MemCycle(re=1, raddr=addr),
        MemCycle(we=1, waddr=addr, wdata=new, wmask=0b0011),
        MemCycle(re=1, raddr=addr),
    ]


def seq_wmask_all(depth: int, width: int, wmask_w: int) -> list[MemCycle]:
    nseg = width // wmask_w
    addr = 0
    data = 0
    for seg in range(nseg):
        data |= _seg_unique(seg, wmask_w)
    return [
        MemCycle(we=1, waddr=addr, wdata=data, wmask=all_seg_mask(nseg)),
        MemCycle(re=1, raddr=addr),
    ]


def seq_wmask_zero(depth: int, width: int, wmask_w: int) -> list[MemCycle]:
    """wmask=0 must not change a previously written word."""
    nseg = width // wmask_w
    addr = 0
    old = _seg_pattern(nseg, wmask_w, 0x3)
    junk = _seg_pattern(nseg, wmask_w, 0xC)
    return [
        MemCycle(we=1, waddr=addr, wdata=old, wmask=all_seg_mask(nseg)),
        MemCycle(re=1, raddr=addr),
        MemCycle(we=1, waddr=addr, wdata=junk, wmask=0),
        MemCycle(re=1, raddr=addr),
    ]


def seq_wmask_conflict(depth: int, width: int, wmask_w: int) -> list[MemCycle]:
    """Same-cycle same-address: every segment reads old."""
    nseg = width // wmask_w
    addr = min(2, depth - 1)
    old = _seg_pattern(nseg, wmask_w, 0x1)
    new = 0
    for seg in range(nseg):
        new |= _seg_unique(seg, wmask_w)
    return [
        MemCycle(we=1, waddr=addr, wdata=old, wmask=all_seg_mask(nseg)),
        MemCycle(
            we=1, waddr=addr, wdata=new, re=1, raddr=addr, wmask=0b0011
        ),
        MemCycle(re=1, raddr=addr),
    ]


def seq_wmask_onehot(depth: int, width: int, wmask_w: int) -> list[MemCycle]:
    """One-hot scan after a baseline fill. Catches reversed wmask order."""
    nseg = width // wmask_w
    addr = 0
    old = _seg_pattern(nseg, wmask_w, 0x4)
    cycles = [
        MemCycle(we=1, waddr=addr, wdata=old, wmask=all_seg_mask(nseg)),
        MemCycle(re=1, raddr=addr),
    ]
    for seg in range(nseg):
        data = _seg_unique(seg, wmask_w)
        # Keep other lanes of wdata distinct so a reversed DUT cannot hide.
        for other in range(nseg):
            if other != seg:
                data |= ((0xA + other) & ((1 << wmask_w) - 1)) << (other * wmask_w)
        cycles.append(MemCycle(we=1, waddr=addr, wdata=data, wmask=1 << seg))
        cycles.append(MemCycle(re=1, raddr=addr))
    return cycles


def seq_wmask_partial_uninit(depth: int, width: int, wmask_w: int) -> list[MemCycle]:
    """Write only segment 0, then read — ANUR=1 is a violation."""
    addr = 0
    return [
        MemCycle(we=1, waddr=addr, wdata=_seg_unique(0, wmask_w), wmask=1 << 0),
        MemCycle(re=1, raddr=addr),
    ]


def _payload(addr: int, width: int) -> int:
    """Not ``addr`` itself — ``data_eq_addr`` is a separate case."""
    return ((addr * 0x9E) ^ 0xA5) & ((1 << width) - 1)


def seq_data_onehot(depth: int, width: int) -> list[MemCycle]:
    """Walk a single data bit through ``rdata``. Catches data-bit swaps."""
    addr = 0
    other = 1 if depth > 1 else 0
    cycles: list[MemCycle] = []
    for bit in range(width):
        data = 1 << bit
        cycles.append(MemCycle(we=1, waddr=addr, wdata=data))
        cycles.append(MemCycle(re=1, raddr=addr))
        if other != addr:
            cycles.append(MemCycle(we=1, waddr=other, wdata=0))
            cycles.append(MemCycle(re=1, raddr=addr))
    return cycles


def seq_addr_onehot(depth: int, width: int) -> list[MemCycle]:
    """Unique payload at 0 and each in-range one-hot address.

    Catches swapped or aliased address bits (a write to 2 must not land in 1).
    """
    cycles: list[MemCycle] = []
    addrs = [0]
    for bit in range(addr_bits(depth)):
        addr = 1 << bit
        if addr < depth:
            addrs.append(addr)
    if 3 < depth:
        addrs.append(3)
    seen: set[int] = set()
    uniq: list[int] = []
    for addr in addrs:
        if addr not in seen:
            seen.add(addr)
            uniq.append(addr)
    for addr in uniq:
        cycles.append(MemCycle(we=1, waddr=addr, wdata=_payload(addr, width)))
    for addr in uniq:
        cycles.append(MemCycle(re=1, raddr=addr))
    return cycles


def seq_fill_fwd_rev(depth: int, width: int) -> list[MemCycle]:
    """Incrementing fill, then forward and reverse readback."""
    mask = (1 << width) - 1
    cycles: list[MemCycle] = []
    for addr in range(depth):
        cycles.append(MemCycle(we=1, waddr=addr, wdata=(addr + 1) & mask))
    for addr in range(depth):
        cycles.append(MemCycle(re=1, raddr=addr))
    for addr in range(depth - 1, -1, -1):
        cycles.append(MemCycle(re=1, raddr=addr))
    return cycles


def seq_data_eq_addr(depth: int, width: int) -> list[MemCycle]:
    mask = (1 << width) - 1
    cycles: list[MemCycle] = []
    for addr in range(depth):
        cycles.append(MemCycle(we=1, waddr=addr, wdata=addr & mask))
    for addr in range(depth):
        cycles.append(MemCycle(re=1, raddr=addr))
    return cycles


def seq_oor_waddr(depth: int, extra: int | None = None) -> list[MemCycle]:
    addr = depth if extra is None else extra
    return [MemCycle(we=1, waddr=addr, wdata=1)]


def seq_oor_raddr(depth: int, extra: int | None = None) -> list[MemCycle]:
    addr = depth if extra is None else extra
    return [
        MemCycle(we=1, waddr=0, wdata=1),
        MemCycle(re=1, raddr=addr),
    ]


def seq_uninit_read(addr: int = 0) -> list[MemCycle]:
    return [MemCycle(re=1, raddr=addr)]


def seq_uninit_same_cycle_write(addr: int = 1, data: int = 0xAA) -> list[MemCycle]:
    return [MemCycle(we=1, waddr=addr, wdata=data, re=1, raddr=addr)]


def make_sequence(
    case: str,
    depth: int,
    width: int,
    seed: int,
    *,
    assert_no_uninit_read: bool = True,
    wmask_w: int | None = None,
    random_n: int | None = None,
) -> list[MemCycle]:
    if wmask_w is None:
        wmask_w = width
    if case == "random":
        n = 80 if random_n is None else int(random_n)
        return seq_random_legal(
            depth,
            width,
            seed,
            n,
            assert_no_uninit_read=assert_no_uninit_read,
            wmask_w=wmask_w,
        )
    if case == "conflict":
        return seq_conflict_read_old(depth, width)
    if case in {"back2back", "back_to_back"}:
        return seq_back_to_back(depth, width)
    if case == "boundary":
        return seq_boundary(depth, width)
    if case == "hold":
        return seq_rdata_hold(addr=0 if depth == 1 else 1)
    if case == "data_onehot":
        return seq_data_onehot(depth, width)
    if case == "addr_onehot":
        return seq_addr_onehot(depth, width)
    if case in {"fill_fwd_rev", "fill"}:
        return seq_fill_fwd_rev(depth, width)
    if case == "data_eq_addr":
        return seq_data_eq_addr(depth, width)
    if case == "oor_waddr":
        return seq_oor_waddr(depth)
    if case == "oor_raddr":
        return seq_oor_raddr(depth)
    if case == "uninit":
        return seq_uninit_read(0)
    if case == "uninit_conflict":
        return seq_uninit_same_cycle_write(0 if depth == 1 else 1)
    if case == "uninit_ok":
        return seq_uninit_read(0)
    if case == "wmask_single":
        return seq_wmask_single(depth, width, wmask_w)
    if case == "wmask_adjacent":
        return seq_wmask_adjacent(depth, width, wmask_w)
    if case == "wmask_all":
        return seq_wmask_all(depth, width, wmask_w)
    if case == "wmask_zero":
        return seq_wmask_zero(depth, width, wmask_w)
    if case == "wmask_conflict":
        return seq_wmask_conflict(depth, width, wmask_w)
    if case == "wmask_onehot":
        return seq_wmask_onehot(depth, width, wmask_w)
    if case in {"wmask_partial_uninit", "wmask_partial_ok"}:
        return seq_wmask_partial_uninit(depth, width, wmask_w)
    raise ValueError(f"unknown case {case!r}")


def expected_violation(case: str, assert_no_uninit_read: bool) -> str | None:
    if case in {"oor_waddr", "oor_raddr"}:
        return "oor"
    if case in {"uninit", "uninit_conflict", "wmask_partial_uninit"} and (
        assert_no_uninit_read
    ):
        return "uninit"
    return None
