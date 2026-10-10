"""Leaf TB: ub_pyc_rst_adapt (SPEC §4.2). Polarity + 0-cycle."""

from __future__ import annotations

import cocotb
from cocotb.triggers import RisingEdge
from uvm import uvm_component_utils

from tb.vibe_uvm.clk_rst import CORE_CLK_PERIOD_PS
from tb.vibe_uvm.leaf_base import LeafUvmTest, as_int, env_int, leaf_entry, wait_ps
from tb.vibe_uvm.leaf_cov import sample_rst_adapt

TP = ["TP-UNIT-RST-002"]


class RstAdaptLeafTest(LeafUvmTest):
    TB_NAME = "ub_pyc_rst_adapt"
    COV_PREFIX = "ub_pyc_rst_adapt"

    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.pol = env_int("PYC_RST_ACTIVE_HIGH", 1)

    def _expect(self, rst_n_sync: int) -> int:
        return (0 if rst_n_sync else 1) if self.pol else rst_n_sync

    async def _drive(self, val: int) -> None:
        self.dut.rst_n_sync.value = val
        await wait_ps(20)

    async def run_cases(self) -> None:
        self.dut.rst_n.value = 1
        await self.case_levels()
        await self.case_combo_0cycle()
        await self.case_not_registered()

    async def case_levels(self) -> None:
        kind = "invert" if self.pol else "wire"
        name = f"polarity_{kind}"
        try:
            for src in (0, 1):
                await self._drive(src)
                got = as_int(self.dut.rst_pyc, "rst_pyc")
                exp = self._expect(src)
                if got != exp:
                    raise AssertionError(
                        f"PYC_RST_ACTIVE_HIGH={self.pol} rst_n_sync={src} "
                        f"rst_pyc={got} expected {exp}"
                    )
            sample_rst_adapt(self.pol, kind, self.hooks)
            self.rec.pass_(name, TP, f"PYC_RST_ACTIVE_HIGH={self.pol}")
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_combo_0cycle(self) -> None:
        name = "combo_0cycle"
        try:
            await self._drive(0)
            t0 = as_int(self.dut.rst_pyc, "rst_pyc")
            await self._drive(1)
            t1 = as_int(self.dut.rst_pyc, "rst_pyc")
            if t0 == t1:
                raise AssertionError("output did not follow input in 0 cycles")
            if t1 != self._expect(1) or t0 != self._expect(0):
                raise AssertionError(f"combo values {t0}->{t1}")
            sample_rst_adapt(self.pol, "combo_0", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_not_registered(self) -> None:
        name = "not_registered"
        try:
            await RisingEdge(self.dut.core_clk)
            await wait_ps(100)
            await self._drive(0)
            mid = as_int(self.dut.rst_pyc, "rst_pyc")
            if mid != self._expect(0):
                raise AssertionError("waits for next edge (registered)")
            await wait_ps(CORE_CLK_PERIOD_PS // 2)
            if as_int(self.dut.rst_pyc, "rst_pyc") != self._expect(0):
                raise AssertionError("changed without input")
            sample_rst_adapt(self.pol, "not_registered", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise


uvm_component_utils(RstAdaptLeafTest)


@cocotb.test()
async def test_ub_rst_adapt(dut):
    await leaf_entry(dut, "RstAdaptLeafTest")
