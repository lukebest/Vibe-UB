"""Contract scoreboard hooks (GATE-TB-SB-001).

Each compare() counts as 1. Segmented compares count per segment.
Paired directions (TX/RX, submit/complete) compare to the model on
each side independently — loopback is never the only check.
"""

from __future__ import annotations

from typing import Any


class ContractScoreboard:
    """Record compares per side and enforce n_compare > 0 and == expected."""

    def __init__(self, name: str, expected: dict[str, int]):
        if "total" not in expected:
            raise ValueError("expected must include 'total'")
        self.name = name
        self.expected = dict(expected)
        self.n_compare = 0
        self.n_mismatch = 0
        self.n_compare_side: dict[str, int] = {
            k: 0 for k in expected if k != "total"
        }
        self.mismatches: list[str] = []

    def compare(self, side: str, exp: Any, actual: Any, ctx: str = "") -> bool:
        if side not in self.n_compare_side:
            raise KeyError(f"{self.name}: unknown side {side!r}")
        self.n_compare += 1
        self.n_compare_side[side] += 1
        if exp == actual:
            return True
        self.n_mismatch += 1
        self.mismatches.append(
            f"{self.name} {side} {ctx}: expected={exp!r} actual={actual!r}"
        )
        return False

    def check(self) -> None:
        if self.n_compare <= 0:
            raise AssertionError(f"{self.name}: n_compare={self.n_compare} (must be > 0)")
        want = int(self.expected["total"])
        if self.n_compare != want:
            raise AssertionError(
                f"{self.name}: n_compare={self.n_compare} != expected {want}"
            )
        for side, want_side in self.expected.items():
            if side == "total":
                continue
            got = self.n_compare_side.get(side, 0)
            if got != int(want_side):
                raise AssertionError(
                    f"{self.name}: side {side} n_compare={got} != expected {want_side}"
                )
        if self.n_mismatch:
            detail = "; ".join(self.mismatches)
            raise AssertionError(
                f"{self.name}: {self.n_mismatch} mismatch(es): {detail}"
            )
