"""Scoreboard: architecture model is the only data oracle (CODING_STYLE §10).

Compare DUT ``rdata`` to ``UbCmnMem1r1w.rdata`` bit-by-bit **only** when
the model marks it defined (``rdata_valid`` / ``is_defined``). When the
model returns ``None``, skip the compare and count the skip. Do not keep a
TB-side ``written[]`` / ``rdata_known`` shadow of that rule.
"""

from __future__ import annotations

from model.ub_cmn_mem_1r1w import UbCmnMem1r1w, UbCmnMemAddrError, UbCmnMemUnwrittenError


class Mem1r1wScoreboard:
    """Lock-step ``UbCmnMem1r1w``; bitwise compare iff the model is defined."""

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
        self.n_skip = 0
        self.n_mismatch = 0
        self.mismatches: list[str] = []
        self.cycle_flags: list[str] = []
        self.all_flags: list[str] = []
        self._n_flags_seen = 0
        self.last_expected: int | None = None

    @property
    def rdata_valid(self) -> bool:
        return self.ref.rdata_valid

    @property
    def is_defined(self) -> bool:
        return self.ref.is_defined

    def predict(
        self,
        we: int | bool,
        waddr: int,
        wdata: int,
        re: int | bool,
        raddr: int,
    ) -> tuple[int | None, list[str]]:
        expected = self.ref.tick(we, waddr, wdata, re, raddr)
        new_flags = self.ref.flags[self._n_flags_seen :]
        self._n_flags_seen = len(self.ref.flags)
        self.cycle_flags = list(new_flags)
        self.all_flags.extend(new_flags)
        self.last_expected = expected
        return expected, list(new_flags)

    def compare_rdata(self, actual, ctx: str = "rdata") -> bool:
        """Skip when the model is undefined; otherwise bitwise vs ``ref.rdata``."""
        if self.ref.rdata_valid != self.ref.is_defined:
            raise AssertionError(
                "model rdata_valid and is_defined diverged: "
                f"valid={self.ref.rdata_valid} defined={self.ref.is_defined}"
            )
        if not self.ref.rdata_valid or self.ref.rdata is None:
            self.n_skip += 1
            return True
        return self._compare_bits(actual, int(self.ref.rdata), ctx)

    def compare(self, actual, expected: int, ctx: str = "rdata") -> bool:
        """Bitwise compare. Callers must only use this when the model is defined."""
        if not self.ref.rdata_valid or self.ref.rdata is None:
            self.n_skip += 1
            return True
        return self._compare_bits(actual, int(expected), ctx)

    def _compare_bits(self, actual, expected: int, ctx: str) -> bool:
        self.n_compare += 1
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
