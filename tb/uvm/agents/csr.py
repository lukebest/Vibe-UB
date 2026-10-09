"""CSR agent: whole-word write, 1-cycle read, check csr_err (SPEC §3.2.3)."""

from __future__ import annotations

from cocotb.triggers import RisingEdge
from uvm.base.uvm_globals import uvm_error
from uvm.comps.uvm_agent import UVMAgent
from uvm.comps.uvm_driver import UVMDriver
from uvm.comps.uvm_monitor import UVMMonitor
from uvm.macros import uvm_component_utils
from uvm.tlm1.uvm_analysis_port import UVMAnalysisPort

from tb.uvm.items import CsrItem


class _CsrVif:
    def __init__(self, dut):
        self.clk = dut.core_clk
        self.req = dut.csr_req
        self.wr = dut.csr_wr
        self.addr = dut.csr_addr
        self.wdata = dut.csr_wdata
        self.ready = dut.csr_ready
        self.rvalid = dut.csr_rvalid
        self.rdata = dut.csr_rdata
        self.err = dut.csr_err


class CsrDriver(UVMDriver):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.vif = None

    def bind(self, vif: _CsrVif) -> None:
        self.vif = vif

    async def idle(self) -> None:
        self.vif.req.value = 0
        self.vif.wr.value = 0
        self.vif.addr.value = 0
        self.vif.wdata.value = 0

    async def access(self, item: CsrItem) -> CsrItem:
        """Issue one req. Response is the next cycle (SPEC §3.2.3)."""
        self.vif.addr.value = item.addr & 0xFFFF
        self.vif.wdata.value = item.wdata & 0xFFFFFFFF
        self.vif.wr.value = 1 if item.write else 0
        self.vif.req.value = 1
        await RisingEdge(self.vif.clk)
        if int(self.vif.ready.value) != 1:
            uvm_error("CSR", "csr_ready was 0; SPEC §3.2.3 says M1 ready is always 1")
        self.vif.req.value = 0
        await RisingEdge(self.vif.clk)
        item.err = int(self.vif.err.value)
        item.rdata = int(self.vif.rdata.value)
        if item.write:
            if int(self.vif.rvalid.value) != 0:
                uvm_error("CSR", "write response must have csr_rvalid=0 (SPEC §3.2.3)")
        else:
            if int(self.vif.rvalid.value) != 1:
                uvm_error("CSR", "read response must have csr_rvalid=1 on the next cycle")
        return item

    async def run_phase(self, phase):
        if self.vif is None:
            return
        await self.idle()
        while True:
            got = []
            await self.seq_item_port.get_next_item(got)
            await self.access(got[0])
            self.seq_item_port.item_done()


class CsrMonitor(UVMMonitor):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.vif = None
        self.ap = UVMAnalysisPort("ap", self)

    def bind(self, vif: _CsrVif) -> None:
        self.vif = vif

    async def run_phase(self, phase):
        if self.vif is None:
            return
        while True:
            await RisingEdge(self.vif.clk)
            if int(self.vif.req.value) == 1 and int(self.vif.ready.value) == 1:
                pending = CsrItem()
                pending.write = int(self.vif.wr.value)
                pending.addr = int(self.vif.addr.value)
                pending.wdata = int(self.vif.wdata.value)
                await RisingEdge(self.vif.clk)
                pending.rdata = int(self.vif.rdata.value)
                pending.err = int(self.vif.err.value)
                self.ap.write(pending)


class CsrAgent(UVMAgent):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.driver = CsrDriver("driver", self)
        self.monitor = CsrMonitor("monitor", self)

    def bind(self, dut) -> None:
        vif = _CsrVif(dut)
        self.driver.bind(vif)
        self.monitor.bind(vif)


uvm_component_utils(CsrDriver)
uvm_component_utils(CsrMonitor)
uvm_component_utils(CsrAgent)
