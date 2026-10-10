"""Directed + random sequences. Seeds are caller-owned (VERIF_PLAN §10.3)."""

from __future__ import annotations

from random import Random

from model.ub_cmn_mem_1r1w import clog2
from tb.cmn.items import MemCycle

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
) -> list[MemCycle]:
    rng = Random(seed)
    written = [False] * depth
    cycles: list[MemCycle] = []
    for _ in range(n):
        item = MemCycle()
        item.randomize_legal(
            rng, depth, width, written, assert_no_uninit_read=assert_no_uninit_read
        )
        cycles.append(item)
        if item.we:
            written[item.waddr] = True
    return cycles


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
) -> list[MemCycle]:
    if case == "random":
        return seq_random_legal(
            depth, width, seed, assert_no_uninit_read=assert_no_uninit_read
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
    raise ValueError(f"unknown case {case!r}")


def expected_violation(case: str, assert_no_uninit_read: bool) -> str | None:
    if case in {"oor_waddr", "oor_raddr"}:
        return "oor"
    if case in {"uninit", "uninit_conflict"} and assert_no_uninit_read:
        return "uninit"
    return None
