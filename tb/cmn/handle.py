"""Fake DUT handle: same port names as the leaf, backed by the architecture model."""

from __future__ import annotations

from model.ub_cmn_mem_1r1w import UbCmnMem1r1w, clog2
from tb.cmn.ports import CLK_PORT, RST_PORT, rst_assert_value, rst_deassert_value


class _Val:
    def __init__(self, value: int = 0) -> None:
        self.value = int(value)


class FakeMemHandle:
    """Records driven cycles and ticks an inner ``UbCmnMem1r1w`` (strict=False).

    Used to prove the TB driver / scoreboard against the model without RTL.
    Clock is ``core_clk``; reset is ``rst_n`` (active-low). Array and rdata
    are not reset; ``apply_reset()`` only marks the array undefined.
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
        self.aw = max(1, clog2(self.depth))
        self.core_clk = _Val(0)
        self.rst_n = _Val(rst_deassert_value())
        if CLK_PORT != "core_clk" or RST_PORT != "rst_n":
            raise RuntimeError(
                f"FakeMemHandle attributes must match contract "
                f"{CLK_PORT}/{RST_PORT}"
            )
        self.we = _Val(0)
        self.waddr = _Val(0)
        self.wdata = _Val(0)
        self.re = _Val(0)
        self.raddr = _Val(0)
        self.rdata = _Val(0)
        self.rdata_defined = False
        self.inner = UbCmnMem1r1w(
            self.depth,
            self.width,
            assert_no_uninit_read=assert_no_uninit_read,
            strict=False,
        )
        self.trace: list[tuple[int, int, int, int, int]] = []

    def sample_inputs(self) -> tuple[int, int, int, int, int]:
        return (
            int(bool(self.we.value)),
            int(self.waddr.value),
            int(self.wdata.value),
            int(bool(self.re.value)),
            int(self.raddr.value),
        )

    def apply_reset(self) -> None:
        """Assert ``rst_n``, mark the array undefined, then deassert.

        Does not clear the rdata register (CODING_STYLE §10).
        """
        self.rst_n.value = rst_assert_value()
        self.inner.reset_written()
        self.rst_n.value = rst_deassert_value()

    def posedge(self) -> int | None:
        """Rising ``core_clk``: apply the currently driven ports to the inner model."""
        cyc = self.sample_inputs()
        self.trace.append(cyc)
        rdata = self.inner.tick(*cyc)
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
        self.trace.append((we, waddr, wdata, re, raddr))
        rdata = self.inner.tick(we, waddr & ~1, wdata, re, raddr & ~1)
        self.rdata_defined = rdata is not None
        if rdata is None:
            return None
        self.rdata.value = int(rdata)
        return int(rdata)
