"""Scoreboard: architecture model is the only data oracle (CODING_STYLE §10).

Every compared cycle is a bit-by-bit check of DUT ``rdata`` against
``model.ub_cmn_mem_1r1w.UbCmnMem1r1w.rdata`` after the same ``tick()``.
A local ``wrote[addr] == read`` loop is not a pass criterion — that pattern
can hide swapped address bits and cancel bugs on both sides of a TB/DUT pair.
"""

from __future__ import annotations

from model.ub_cmn_mem_1r1w import UbCmnMem1r1w, UbCmnMemAddrError, UbCmnMemUnwrittenError


class Mem1r1wScoreboard:
    """Lock-step ``UbCmnMem1r1w``; bitwise ``rdata`` compare; violation flags.

    ``strict=False`` so a cycle can update the array and still record a
    violation (same-cycle uninit read-old still writes). Callers decide
    whether flags are expected. Legal traffic is never relaxed: after an
    in-range read of a previously written entry, every ``rdata`` bit must
    match the model, including hold cycles.
    """

    def __init__(
        self,
        depth: int,
        width: int,
        *,
        assert_no_uninit_read: bool = True,
    ) -> None:
        self.depth = int(depth)
        self.width = int(width)
        self.mask = (1 << self.width) - 1
        self.assert_no_uninit_read = bool(assert_no_uninit_read)
        self.ref = UbCmnMem1r1w(
            self.depth,
            self.width,
            assert_no_uninit_read=self.assert_no_uninit_read,
            strict=False,
        )
        self.n_compare = 0
        self.n_mismatch = 0
        self.mismatches: list[str] = []
        self.cycle_flags: list[str] = []
        self.all_flags: list[str] = []
        self.rdata_known = False
        self._n_flags_seen = 0
        self.last_expected = 0

    def predict(
        self,
        we: int | bool,
        waddr: int,
        wdata: int,
        re: int | bool,
        raddr: int,
    ) -> tuple[int, list[str]]:
        written_before = self.ref.written
        expected = self.ref.tick(we, waddr, wdata, re, raddr) & self.mask
        new_flags = self.ref.flags[self._n_flags_seen :]
        self._n_flags_seen = len(self.ref.flags)
        self.cycle_flags = list(new_flags)
        self.all_flags.extend(new_flags)
        self.last_expected = int(expected)

        in_range = bool(re) and 0 <= int(raddr) < self.depth
        if in_range and written_before[int(raddr)]:
            self.rdata_known = True
        elif in_range and not written_before[int(raddr)]:
            # RTL array is not reset: unwritten read is X; model returns 0.
            self.rdata_known = False
        return int(expected), list(new_flags)

    def compare_rdata(self, actual, ctx: str = "rdata") -> bool:
        """Bit-by-bit vs ``self.ref.rdata``. ``actual is None`` means X/Z."""
        expected = int(self.ref.rdata) & self.mask
        return self.compare(actual, expected, ctx)

    def compare(
        self,
        actual,
        expected: int,
        ctx: str = "rdata",
        *,
        require_known: bool = True,
    ) -> bool:
        self.n_compare += 1
        if require_known and not self.rdata_known:
            return True
        if actual is None:
            self.n_mismatch += 1
            self.mismatches.append(f"{ctx}: expected={expected:#x} actual=X/Z")
            return False
        got = int(actual) & self.mask
        exp = int(expected) & self.mask
        bad: list[str] = []
        for bit in range(self.width):
            a = (got >> bit) & 1
            e = (exp >> bit) & 1
            if a != e:
                bad.append(f"bit{bit} exp={e} got={a}")
        if bad:
            self.n_mismatch += 1
            self.mismatches.append(
                f"{ctx}: {', '.join(bad)} exp={exp:#x} got={got:#x}"
            )
            return False
        return True

    def saw(self, kind: str) -> bool:
        token = {
            "oor": "UbCmnMemAddrError",
            "addr": "UbCmnMemAddrError",
            "uninit": "UbCmnMemUnwrittenError",
            "unwritten": "UbCmnMemUnwrittenError",
        }.get(kind, kind)
        return any(token in flag for flag in self.all_flags)

    def last_saw(self, kind: str) -> bool:
        token = {
            "oor": "UbCmnMemAddrError",
            "addr": "UbCmnMemAddrError",
            "uninit": "UbCmnMemUnwrittenError",
            "unwritten": "UbCmnMemUnwrittenError",
        }.get(kind, kind)
        return any(token in flag for flag in self.cycle_flags)

    def assert_clean(self) -> None:
        if self.all_flags:
            raise AssertionError(
                "scoreboard recorded unexpected violations: " + "; ".join(self.all_flags)
            )
        if self.n_mismatch:
            raise AssertionError(
                f"{self.n_mismatch} scoreboard mismatches: " + "; ".join(self.mismatches)
            )


__all__ = [
    "Mem1r1wScoreboard",
    "UbCmnMemAddrError",
    "UbCmnMemUnwrittenError",
]
