"""Drive ``ub_cmn_mem_1r1w`` ports. Handle is any object with ``.value`` signals."""

from __future__ import annotations

from tb.cmn.items import MemCycle
from tb.cmn.ports import CLK_PORT, RST_PORT, rst_assert_value, rst_deassert_value


class Mem1r1wDriver:
    """Synchronous port driver. Does not force internals (VERIF_PLAN §5.5 / D13)."""

    def drive(self, handle, cycle: MemCycle) -> None:
        handle.we.value = int(bool(cycle.we))
        handle.waddr.value = int(cycle.waddr)
        handle.wdata.value = int(cycle.wdata)
        handle.re.value = int(bool(cycle.re))
        handle.raddr.value = int(cycle.raddr)

    def idle(self, handle) -> None:
        self.drive(handle, MemCycle())

    def apply_reset(self, handle, *, asserted: bool) -> None:
        rst = getattr(handle, RST_PORT, None)
        if rst is None:
            raise AttributeError(
                f"handle has no reset port '{RST_PORT}' "
                f"(clock must be '{CLK_PORT}')"
            )
        rst.value = rst_assert_value() if asserted else rst_deassert_value()
