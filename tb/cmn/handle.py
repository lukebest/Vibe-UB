"""Fake DUT handle: same port names as the leaf, backed by the architecture model."""

from __future__ import annotations

from model.ub_cmn_mem_1r1w import UbCmnMem1r1w, clog2
from tb.cmn.items import all_seg_mask
from tb.cmn.ports import CLK_PORT


class _Val:
    def __init__(self, value: int = 0) -> None:
        self.value = int(value)


class FakeMemHandle:
    """Records driven cycles and ticks an inner ``UbCmnMem1r1w`` (strict=False).

    Clock is ``core_clk``. The leaf has no reset port. ``undefine_array()``
    calls the model ``reset_written()`` (array undefined; rdata holds).
    ``NSEG>1`` exposes ``wmask``; ``NSEG=1`` does not.
    """

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
        self.aw = max(1, clog2(self.depth))
        self.core_clk = _Val(0)
        if CLK_PORT != "core_clk":
            raise RuntimeError(f"FakeMemHandle clock must be {CLK_PORT}")
        self.we = _Val(0)
        self.waddr = _Val(0)
        self.wdata = _Val(0)
        self.re = _Val(0)
        self.raddr = _Val(0)
        self.rdata = _Val(0)
        self.rdata_defined = False
        if self.nseg > 1:
            self.wmask = _Val(all_seg_mask(self.nseg))
        self.inner = UbCmnMem1r1w(
            self.depth,
            self.width,
            wmask_w=self.wmask_w,
            assert_no_uninit_read=assert_no_uninit_read,
            strict=False,
        )
        self.trace: list[tuple] = []

    def sample_inputs(self) -> tuple[int, int, int, int, int]:
        return (
            int(bool(self.we.value)),
            int(self.waddr.value),
            int(self.wdata.value),
            int(bool(self.re.value)),
            int(self.raddr.value),
        )

    def resolved_wmask(self) -> int:
        if self.nseg <= 1:
            return 1
        return int(self.wmask.value) & all_seg_mask(self.nseg)

    def tick_args(self) -> tuple:
        base = self.sample_inputs()
        if self.nseg <= 1:
            return base
        return base + (self.resolved_wmask(),)

    def undefine_array(self) -> None:
        """Mark the array undefined. Does not clear the rdata register."""
        self.inner.reset_written()

    def posedge(self) -> int | None:
        """Rising ``core_clk``: apply the currently driven ports to the inner model."""
        cyc = self.tick_args()
        self.trace.append(cyc)
        rdata = self.inner.tick(*cyc) if self.nseg == 1 else self.inner.tick(
            *cyc[:5], wmask=cyc[5]
        )
        self.rdata_defined = rdata is not None
        if rdata is None:
            return None
        self.rdata.value = int(rdata)
        return int(rdata)


class BitSwapFakeHandle(FakeMemHandle):
    """Swaps ``rdata`` bits 0 and 1. Scoreboard must fail against the model."""

    def posedge(self) -> int | None:
        rdata = super().posedge()
        if rdata is None:
            return None
        if self.width >= 2:
            b0, b1 = rdata & 1, (rdata >> 1) & 1
            rdata = (rdata & ~3) | (b0 << 1) | b1
            self.rdata.value = rdata
        return int(self.rdata.value)


class AddrAliasFakeHandle(FakeMemHandle):
    """Drops address bit 0 on the inner model. Scoreboard must fail."""

    def posedge(self) -> int | None:
        we, waddr, wdata, re, raddr = self.sample_inputs()
        wmask = self.resolved_wmask() if self.nseg > 1 else None
        if self.nseg > 1:
            self.trace.append((we, waddr, wdata, re, raddr, wmask))
        else:
            self.trace.append((we, waddr, wdata, re, raddr))
        rdata = self.inner.tick(
            we, waddr & ~1, wdata, re, raddr & ~1, wmask=wmask
        )
        self.rdata_defined = rdata is not None
        if rdata is None:
            return None
        self.rdata.value = int(rdata)
        return int(rdata)


class WmaskSwapFakeHandle(FakeMemHandle):
    """Reverses ``wmask`` bit order. Scoreboard must fail (catches swapped segs)."""

    def posedge(self) -> int | None:
        we, waddr, wdata, re, raddr = self.sample_inputs()
        wmask = self.resolved_wmask()
        if self.nseg > 1:
            self.trace.append((we, waddr, wdata, re, raddr, wmask))
        else:
            self.trace.append((we, waddr, wdata, re, raddr))
        rev = 0
        for seg in range(self.nseg):
            if wmask & (1 << seg):
                rev |= 1 << (self.nseg - 1 - seg)
        rdata = self.inner.tick(we, waddr, wdata, re, raddr, wmask=rev)
        self.rdata_defined = rdata is not None
        if rdata is None:
            return None
        self.rdata.value = int(rdata)
        return int(rdata)
