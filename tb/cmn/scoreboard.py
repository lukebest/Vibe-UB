"""Scoreboard: architecture model is the only data oracle (CODING_STYLE §10).

Compare DUT ``rdata`` to ``UbCmnMem1r1w.rdata`` **only** on segments the
model marks valid (``rdata_valid`` / ``valid_mask``). ``NSEG=1`` keeps
the bool / whole-word path. ``NSEG>1`` uses ``compare_valid_segments()``
and counts compares per segment. Do not keep a TB-side ``written[]``
shadow of that rule.
"""

from __future__ import annotations

from model.ub_cmn_mem_1r1w import UbCmnMem1r1w, UbCmnMemAddrError, UbCmnMemUnwrittenError


class Mem1r1wScoreboard:
    """Lock-step ``UbCmnMem1r1w``; compare only model-valid segments."""

    def __init__(
        self,
        depth: int,
        width: int,
        *,
        wmask_w: int | None = None,
        assert_no_uninit_read: bool = True,
    ) -> None:
        self.depth = int(depth)
        self.width = int(width)
        self.wmask_w = int(self.width if wmask_w is None else wmask_w)
        self.nseg = self.width // self.wmask_w
        self.mask = (1 << self.width) - 1
        self.assert_no_uninit_read = bool(assert_no_uninit_read)
        self.ref = UbCmnMem1r1w(
            self.depth,
            self.width,
            wmask_w=self.wmask_w,
            assert_no_uninit_read=self.assert_no_uninit_read,
            strict=False,
        )
        self.n_compare = 0
        self.n_skip = 0
        self.n_mismatch = 0
        self.n_compare_seg = [0] * self.nseg
        self.mismatches: list[str] = []
        self.cycle_flags: list[str] = []
        self.all_flags: list[str] = []
        self._n_flags_seen = 0
        self.last_expected: int | None = None

    @property
    def rdata_valid(self):
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
        wmask: int | None = None,
    ) -> tuple[int | None, list[str]]:
        expected = self.ref.tick(we, waddr, wdata, re, raddr, wmask=wmask)
        new_flags = self.ref.flags[self._n_flags_seen :]
        self._n_flags_seen = len(self.ref.flags)
        self.cycle_flags = list(new_flags)
        self.all_flags.extend(new_flags)
        self.last_expected = expected
        return expected, list(new_flags)

    def compare_rdata(self, actual, ctx: str = "rdata") -> bool:
        """Skip undefined segments; otherwise bitwise vs ``ref.rdata``."""
        if self.nseg == 1:
            if self.ref.rdata_valid != self.ref.is_defined:
                raise AssertionError(
                    "model rdata_valid and is_defined diverged: "
                    f"valid={self.ref.rdata_valid} defined={self.ref.is_defined}"
                )
            if not self.ref.rdata_valid or self.ref.rdata is None:
                self.n_skip += 1
                return True
            return self._compare_bits(actual, int(self.ref.rdata), ctx)
        return self._compare_segments(actual, ctx)

    def compare(self, actual, expected: int, ctx: str = "rdata") -> bool:
        """Bitwise compare. Callers must only use this when the model is defined."""
        if self.nseg == 1:
            if not self.ref.rdata_valid or self.ref.rdata is None:
                self.n_skip += 1
                return True
            return self._compare_bits(actual, int(expected), ctx)
        return self._compare_segments(actual, ctx, expected=int(expected))

    def _compare_bits(self, actual, expected: int, ctx: str) -> bool:
        self.n_compare += 1
        self.n_compare_seg[0] += 1
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

    def _compare_segments(
        self, actual, ctx: str, *, expected: int | None = None
    ) -> bool:
        vm = self.ref.valid_mask
        exp_word = self.ref.rdata if expected is None else expected
        if vm == 0 or exp_word is None:
            self.n_skip += self.nseg
            return True
        if actual is None:
            for seg in range(self.nseg):
                if vm & (1 << seg):
                    self.n_compare += 1
                    self.n_compare_seg[seg] += 1
                    self.n_mismatch += 1
                    self.mismatches.append(
                        f"{ctx}: seg{seg} expected={self.ref.segment_bits(int(exp_word), seg):#x} actual=X/Z"
                    )
                else:
                    self.n_skip += 1
            return False
        got = int(actual) & self.mask
        exp = int(exp_word) & self.mask
        ok = True
        for seg in range(self.nseg):
            if not (vm & (1 << seg)):
                self.n_skip += 1
                continue
            self.n_compare += 1
            self.n_compare_seg[seg] += 1
            a = self.ref.segment_bits(got, seg)
            e = self.ref.segment_bits(exp, seg)
            if a != e:
                ok = False
                self.n_mismatch += 1
                self.mismatches.append(
                    f"{ctx}: seg{seg} exp={e:#x} got={a:#x} "
                    f"(wmask_w={self.wmask_w})"
                )
        return ok

    def assert_seg_compares(
        self,
        *,
        compared: list[int] | None = None,
        untouched: list[int] | None = None,
        expected: list[int] | None = None,
        min_each: int | None = None,
    ) -> None:
        """Self-check: per-segment compare counts > 0 and/or equal expected."""
        if expected is not None:
            got = list(self.n_compare_seg)
            want = list(expected)
            if got != want:
                raise AssertionError(
                    f"per-segment n_compare {got} != expected {want}"
                )
        if compared is not None:
            for seg in compared:
                if self.n_compare_seg[int(seg)] <= 0:
                    raise AssertionError(
                        f"segment {seg} was never compared "
                        f"(n_compare_seg={self.n_compare_seg})"
                    )
        if untouched is not None:
            for seg in untouched:
                if self.n_compare_seg[int(seg)] != 0:
                    raise AssertionError(
                        f"segment {seg} was compared "
                        f"{self.n_compare_seg[int(seg)]} time(s); expected 0"
                    )
        if min_each is not None:
            for seg, n in enumerate(self.n_compare_seg):
                if n < min_each:
                    raise AssertionError(
                        f"segment {seg} n_compare={n} < {min_each}"
                    )
        if self.n_compare != sum(self.n_compare_seg):
            raise AssertionError(
                f"n_compare={self.n_compare} != sum(n_compare_seg)="
                f"{sum(self.n_compare_seg)}"
            )

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
