"""Drive ``ub_cmn_mem_1r1w`` ports. Handle is any object with ``.value`` signals."""

from __future__ import annotations

from tb.cmn.items import MemCycle


class Mem1r1wDriver:
    """Synchronous port driver. Does not force internals (VERIF_PLAN §5.5 / D13)."""

    def drive(self, handle, cycle: MemCycle) -> None:
        handle.we.value = int(bool(cycle.we))
        handle.waddr.value = int(cycle.waddr)
        handle.wdata.value = int(cycle.wdata)
        handle.re.value = int(bool(cycle.re))
        handle.raddr.value = int(cycle.raddr)
        if hasattr(handle, "wmask"):
            nseg = getattr(handle, "nseg", None)
            if nseg is None:
                nseg = len(handle.wmask)
            handle.wmask.value = cycle.resolved_wmask(int(nseg))

    def idle(self, handle) -> None:
        self.drive(handle, MemCycle())
