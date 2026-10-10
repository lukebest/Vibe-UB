"""ub_env: clock/reset, stream agents, CSR, hooks, scoreboard (VERIF_PLAN §5.1)."""

from __future__ import annotations

from uvm import UVMEnv, uvm_component_utils

from tb.vibe_uvm.agents.csr import CsrAgent
from tb.vibe_uvm.agents.hook import HookAgent
from tb.vibe_uvm.agents.valid_only import ValidOnlyAgent
from tb.vibe_uvm.agents.valid_ready import ValidReadyAgent
from tb.vibe_uvm.clk_rst import ClkRstAgent
from tb.vibe_uvm.scoreboard import ScoreboardBase


class UbEnv(UVMEnv):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.clk_rst = ClkRstAgent("clk_rst", self)
        self.vr = ValidReadyAgent("vr", self)
        self.vo = ValidOnlyAgent("vo", self)
        self.csr = CsrAgent("csr", self)
        self.hook = HookAgent("hook", self)
        self.scoreboard = ScoreboardBase("scoreboard", self)
        self.dut = None

    def bind(self, dut) -> None:
        self.dut = dut
        self.clk_rst.bind(dut.core_clk, dut.rst_n)
        self.vr.bind(dut.core_clk, dut.vr_in_data, dut.vr_in_valid, dut.vr_in_ready, is_master=True)
        self.vo.bind(dut.core_clk, dut.vo_in_data, dut.vo_in_valid)
        self.csr.bind(dut)
        self.hook.bind(dut)


uvm_component_utils(UbEnv)
