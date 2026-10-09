"""Generic valid-only driver, monitor, agent (SPEC §3.1). No ready; sink must take it.

PR #5 leaves (scramble / BCRC / lane dist) are valid-only; wire those
ports through this agent. Do not import PR #5 sources.

from __future__ import annotations

from cocotb.triggers import RisingEdge
from uvm import UVMAgent, UVMAnalysisPort, UVMDriver, UVMMonitor, uvm_component_utils

from tb.vibe_uvm.items import VoItem


class _VoVif:
    def __init__(self, clk, data, valid):
        self.clk = clk
        self.data = data
        self.valid = valid


class ValidOnlyDriver(UVMDriver):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.vif = None

    def bind(self, vif: _VoVif) -> None:
        self.vif = vif

    async def drive_item(self, item: VoItem) -> None:
        self.vif.data.value = item.data
        self.vif.valid.value = 1
        await RisingEdge(self.vif.clk)
        self.vif.valid.value = 0

    async def run_phase(self, phase):
        if self.vif is None:
            return
        self.vif.valid.value = 0
        if self.seq_item_port is None or getattr(self.seq_item_port, "m_imp", None) is None:
            return
        while True:
            got = []
            await self.seq_item_port.get_next_item(got)
            await self.drive_item(got[0])
            self.seq_item_port.item_done()


class ValidOnlyMonitor(UVMMonitor):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.vif = None
        self.ap = UVMAnalysisPort("ap", self)

    def bind(self, vif: _VoVif) -> None:
        self.vif = vif

    async def run_phase(self, phase):
        if self.vif is None:
            return
        while True:
            await RisingEdge(self.vif.clk)
            if int(self.vif.valid.value) == 1:
                item = VoItem()
                item.data = int(self.vif.data.value)
                self.ap.write(item)


class ValidOnlyAgent(UVMAgent):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.driver = ValidOnlyDriver("driver", self)
        self.monitor = ValidOnlyMonitor("monitor", self)

    def bind(self, clk, data, valid) -> None:
        vif = _VoVif(clk, data, valid)
        self.driver.bind(vif)
        self.monitor.bind(vif)


uvm_component_utils(ValidOnlyDriver)
uvm_component_utils(ValidOnlyMonitor)
uvm_component_utils(ValidOnlyAgent)
