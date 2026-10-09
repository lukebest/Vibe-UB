"""Generic valid/ready driver, monitor, agent (SPEC §3.1)."""

from __future__ import annotations

from cocotb.triggers import RisingEdge
from uvm.comps.uvm_agent import UVMAgent
from uvm.comps.uvm_driver import UVMDriver
from uvm.comps.uvm_monitor import UVMMonitor
from uvm.macros import uvm_component_utils
from uvm.tlm1.uvm_analysis_port import UVMAnalysisPort

from tb.uvm.items import VrItem


class _VrVif:
    def __init__(self, clk, data, valid, ready):
        self.clk = clk
        self.data = data
        self.valid = valid
        self.ready = ready


class ValidReadyDriver(UVMDriver):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.vif = None
        self.is_master = True

    def bind(self, vif: _VrVif, is_master: bool = True) -> None:
        self.vif = vif
        self.is_master = is_master

    async def drive_item(self, item: VrItem) -> None:
        if self.is_master:
            self.vif.data.value = item.data
            self.vif.valid.value = 1
            await RisingEdge(self.vif.clk)
            while int(self.vif.ready.value) != 1:
                await RisingEdge(self.vif.clk)
            self.vif.valid.value = 0
        else:
            self.vif.ready.value = 1
            await RisingEdge(self.vif.clk)

    async def run_phase(self, phase):
        if self.vif is None:
            return
        if self.is_master:
            self.vif.valid.value = 0
        else:
            self.vif.ready.value = 1
        while True:
            got = []
            await self.seq_item_port.get_next_item(got)
            await self.drive_item(got[0])
            self.seq_item_port.item_done()


class ValidReadyMonitor(UVMMonitor):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.vif = None
        self.ap = UVMAnalysisPort("ap", self)

    def bind(self, vif: _VrVif) -> None:
        self.vif = vif

    async def run_phase(self, phase):
        if self.vif is None:
            return
        while True:
            await RisingEdge(self.vif.clk)
            if int(self.vif.valid.value) == 1 and int(self.vif.ready.value) == 1:
                item = VrItem()
                item.data = int(self.vif.data.value)
                self.ap.write(item)


class ValidReadyAgent(UVMAgent):
    """Master drives valid+data; slave drives ready. Monitor sees completed beats."""

    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.driver = ValidReadyDriver("driver", self)
        self.monitor = ValidReadyMonitor("monitor", self)
        self.vif = None

    def bind(self, clk, data, valid, ready, is_master: bool = True) -> None:
        self.vif = _VrVif(clk, data, valid, ready)
        self.driver.bind(self.vif, is_master=is_master)
        self.monitor.bind(self.vif)


uvm_component_utils(ValidReadyDriver)
uvm_component_utils(ValidReadyMonitor)
uvm_component_utils(ValidReadyAgent)
