"""Directed + random plans for ``ub_tp_bypass`` (LAYER_CONTRACTS §2 / §3)."""

from __future__ import annotations

import random
from typing import Iterable

from tb.tp.items import RxSpec, TxSpec

# (kind, payload) — kind in {tx, rx, flush, link_down, link_up, end_flush}
Step = tuple[str, object]

DIRECTED_CASES: tuple[str, ...] = (
    "single_tx",
    "multi_tx",
    "dcna_map",
    "onehot_data",
    "rx_clean",
    "rx_err",
    "rx_multi_err",
    "mixed",
    "flush_idle",
    "link_down_idle",
)

DUT_CASES: tuple[str, ...] = DIRECTED_CASES + ("random", "backpressure")


def _tx(data: Iterable[int], dcna: int, tassn: int) -> Step:
    return ("tx", TxSpec(data=tuple(int(x) for x in data), dcna=int(dcna), tassn=int(tassn)))


def _rx(data: Iterable[int], *, err: bool = False, drop: bool = False) -> Step:
    return ("rx", RxSpec(data=tuple(int(x) for x in data), err=err, drop=drop))


def plan_single_tx(tassn: int = 1) -> list[Step]:
    return [_tx((0xA5A5,), 0x1234, tassn)]


def plan_multi_tx(tassn: int = 2) -> list[Step]:
    return [_tx((0x111, 0x222, 0x333, 0x444), 0x55AA, tassn)]


def plan_dcna_map(start: int = 10) -> list[Step]:
    values = (0x0000, 0x0001, 0x8000, 0xFFFF, 0x00AB)
    return [_tx((0x10 + i,), dcna, start + i) for i, dcna in enumerate(values)]


def plan_onehot_data(start: int = 20) -> list[Step]:
    bits = (0, 1, 2, 7, 8, 16, 32, 63, 127, 159)
    return [
        _tx((1 << bit,), 0x0001 + i, start + i) for i, bit in enumerate(bits)
    ]


def plan_rx_clean() -> list[Step]:
    return [_rx((0x5A5A,))]


def plan_rx_err() -> list[Step]:
    return [_rx((0xBEEF,), err=True)]


def plan_rx_multi_err() -> list[Step]:
    return [_rx((0xA, 0xB, 0xC), err=True)]


def plan_mixed(start: int = 40) -> list[Step]:
    return [
        _tx((0x1,), 0x1111, start),
        _rx((0x2,), err=False),
        _tx((0x3, 0x4), 0x2222, start + 1),
        _rx((0x5, 0x6), err=True),
    ]


def plan_flush_idle(start: int = 50) -> list[Step]:
    return [
        _tx((0x77,), 0x0F0F, start),
        ("flush", True),
        ("end_flush", True),
        _tx((0x88,), 0xF0F0, start + 1),
    ]


def plan_link_down_idle(start: int = 60) -> list[Step]:
    return [
        _tx((0x99,), 0x00AA, start),
        ("link_down", True),
        ("link_up", True),
        _tx((0xAA,), 0x00BB, start + 1),
    ]


def plan_drop_then_keep() -> list[Step]:
    """Model-only: drop has no DUT pin."""
    return [
        _rx((0x55,), drop=True, err=True),
        _rx((0x66,), drop=False),
    ]


def plan_random(seed: int, n_tx: int = 8, n_rx: int = 8) -> list[Step]:
    rng = random.Random(int(seed))
    steps: list[Step] = []
    tassn = 100
    for _ in range(int(n_tx)):
        n = rng.randint(1, 4)
        data = tuple(rng.randrange(1 << 32) for _ in range(n))
        dcna = rng.randrange(1 << 16)
        steps.append(_tx(data, dcna, tassn))
        tassn += 1
    for _ in range(int(n_rx)):
        n = rng.randint(1, 4)
        data = tuple(rng.randrange(1 << 32) for _ in range(n))
        steps.append(_rx(data, err=bool(rng.getrandbits(1))))
    rng.shuffle(steps)
    return steps


def make_plan(case: str, *, seed: int = 1) -> list[Step]:
    builders = {
        "single_tx": plan_single_tx,
        "multi_tx": plan_multi_tx,
        "dcna_map": plan_dcna_map,
        "onehot_data": plan_onehot_data,
        "rx_clean": plan_rx_clean,
        "rx_err": plan_rx_err,
        "rx_multi_err": plan_rx_multi_err,
        "mixed": plan_mixed,
        "flush_idle": plan_flush_idle,
        "link_down_idle": plan_link_down_idle,
        "drop_then_keep": plan_drop_then_keep,
        "random": lambda: plan_random(seed),
        "backpressure": lambda: plan_random(seed, n_tx=6, n_rx=6),
    }
    if case == "all":
        out: list[Step] = []
        for name in DIRECTED_CASES:
            out.extend(builders[name]())
        out.extend(plan_random(seed))
        return out
    try:
        return builders[case]()
    except KeyError as exc:
        raise ValueError(f"unknown case {case!r}") from exc


def expected_compares(plan: list[Step]) -> int:
    n = 0
    for kind, payload in plan:
        if kind == "tx":
            n += 1
        elif kind == "rx" and not getattr(payload, "drop", False):
            n += 1
    return n


__all__ = [
    "DIRECTED_CASES",
    "DUT_CASES",
    "Step",
    "expected_compares",
    "make_plan",
    "plan_drop_then_keep",
    "plan_random",
    "plan_single_tx",
]
