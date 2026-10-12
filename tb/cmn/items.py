"""1R1W cycle item. Port names match model + formal/cmn (CODING_STYLE §10)."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random


def all_seg_mask(nseg: int) -> int:
    return (1 << int(nseg)) - 1


@dataclass
class MemCycle:
    """One ``core_clk`` of ``we/waddr/wdata/[wmask]`` + ``re/raddr``.

    ``wmask`` is ``None`` (all-1s) when omitted. ``NSEG=1`` has no
    architectural ``wmask`` port; the field still defaults to all-1s.
    """

    we: int = 0
    waddr: int = 0
    wdata: int = 0
    re: int = 0
    raddr: int = 0
    wmask: int | None = None

    def resolved_wmask(self, nseg: int) -> int:
        if self.wmask is None:
            return all_seg_mask(nseg)
        return int(self.wmask) & all_seg_mask(nseg)

    def as_tuple(self) -> tuple[int, int, int, int, int]:
        return (
            int(bool(self.we)),
            int(self.waddr),
            int(self.wdata),
            int(bool(self.re)),
            int(self.raddr),
        )

    def as_driven(self, nseg: int = 1) -> tuple:
        base = self.as_tuple()
        if int(nseg) <= 1:
            return base
        return base + (self.resolved_wmask(nseg),)

    def randomize_legal(
        self,
        rng: Random,
        depth: int,
        width: int,
        written: list[int],
        *,
        assert_no_uninit_read: bool = True,
        wmask_w: int | None = None,
    ) -> MemCycle:
        """Fill with in-range traffic. Avoids uninit reads when the assert is on."""
        if wmask_w is None:
            wmask_w = width
        nseg = width // int(wmask_w)
        all_seg = all_seg_mask(nseg)
        self.we = rng.randrange(2)
        self.re = rng.randrange(2)
        self.waddr = rng.randrange(depth)
        self.raddr = rng.randrange(depth)
        self.wdata = rng.randrange(1 << width)
        if nseg > 1:
            self.wmask = rng.randrange(1 << nseg)
        else:
            self.wmask = None
        if self.re and assert_no_uninit_read and written[self.raddr] != all_seg:
            self.re = 0
        return self
