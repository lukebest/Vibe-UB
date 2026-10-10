"""1R1W cycle item. Port names match model + formal/cmn (CODING_STYLE §10)."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass
class MemCycle:
    """One ``core_clk`` of ``we/waddr/wdata`` + ``re/raddr``. No reset port."""

    we: int = 0
    waddr: int = 0
    wdata: int = 0
    re: int = 0
    raddr: int = 0

    def as_tuple(self) -> tuple[int, int, int, int, int]:
        return (
            int(bool(self.we)),
            int(self.waddr),
            int(self.wdata),
            int(bool(self.re)),
            int(self.raddr),
        )

    def randomize_legal(
        self,
        rng: Random,
        depth: int,
        width: int,
        written: list[bool],
        *,
        assert_no_uninit_read: bool = True,
    ) -> MemCycle:
        """Fill with in-range traffic. Avoids uninit reads when the assert is on."""
        self.we = rng.randrange(2)
        self.re = rng.randrange(2)
        self.waddr = rng.randrange(depth)
        self.raddr = rng.randrange(depth)
        self.wdata = rng.randrange(1 << width)
        if self.re and assert_no_uninit_read and not written[self.raddr]:
            self.re = 0
        return self
