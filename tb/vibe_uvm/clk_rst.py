"""core_clk ≈ 80.57 MHz; rst_n async assert, sync deassert (SPEC §3.2.1 / §4.2)."""

from __future__ import annotations

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from uvm import UVMComponent, uvm_component_utils

# F_CORE = 2.578125e9 / 32  (SPEC §4.1)
CORE_CLK_PERIOD_PS = 12410  # 12.410 ns ≈ 80.58 MHz (target 80.57 MHz)


class ClkRstAgent(UVMComponent):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.clk = None
        self.rst_n = None
        self.period_ps = CORE_CLK_PERIOD_PS

    def connect_phase(self, phase):
        super().connect_phase(phase)

    def bind(self, clk, rst_n, period_ps: int | None = None) -> None:
        self.clk = clk
        self.rst_n = rst_n
        if period_ps is not None:
            self.period_ps = period_ps

    def start_clock(self) -> None:
        cocotb.start_soon(Clock(self.clk, self.period_ps, units="ps").start())

    async def apply_reset(self, cycles: int = 8) -> None:
        """Async assert, hold, then release on a clock edge (sync deassert)."""
        self.rst_n.value = 0
        await Timer(self.period_ps * 2, units="ps")
        for _ in range(max(1, cycles)):
            await RisingEdge(self.clk)
        await RisingEdge(self.clk)
        self.rst_n.value = 1
        await RisingEdge(self.clk)


uvm_component_utils(ClkRstAgent)
