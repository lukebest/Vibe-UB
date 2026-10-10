"""Leaf TB: ub_rst_sync (SPEC §4.2; CODING_STYLE §2). 2-stage async assert / sync deassert."""

from __future__ import annotations

import cocotb
from cocotb.triggers import RisingEdge
from uvm import uvm_component_utils

from tb.vibe_uvm.clk_rst import CORE_CLK_PERIOD_PS
from tb.vibe_uvm.leaf_base import LeafUvmTest, as_int, leaf_entry, wait_ps
from tb.vibe_uvm.leaf_cov import sample_rst_sync

TP = ["TP-UNIT-RST-001", "TP-UNIT-CDC-001"]
PHASES = ("after_posedge", "after_negedge", "mid_high", "mid_low")


class RstSyncLeafTest(LeafUvmTest):
    TB_NAME = "ub_rst_sync"
    COV_PREFIX = "ub_rst_sync"

    async def _phase_delay(self, phase: str) -> None:
        await RisingEdge(self.dut.core_clk)
        if phase == "after_posedge":
            await wait_ps(100)
        elif phase == "after_negedge":
            await wait_ps(CORE_CLK_PERIOD_PS // 2)
        elif phase == "mid_high":
            await wait_ps(CORE_CLK_PERIOD_PS // 4)
        elif phase == "mid_low":
            await wait_ps((3 * CORE_CLK_PERIOD_PS) // 4)
        else:
            raise ValueError(phase)

    async def _released(self) -> None:
        self.dut.rst_n.value = 1
        for _ in range(4):
            await RisingEdge(self.dut.core_clk)
        if as_int(self.dut.rst_n_sync, "rst_n_sync") != 1:
            raise AssertionError("failed to leave reset")

    async def _assert_immediate(self, ctx: str) -> None:
        self.dut.rst_n.value = 0
        await wait_ps(20)
        got = as_int(self.dut.rst_n_sync, "rst_n_sync")
        if got != 0:
            raise AssertionError(f"{ctx}: async assert not immediate, rst_n_sync={got}")

    async def run_cases(self) -> None:
        await self.case_async_assert_any_phase()
        await self.case_sync_deassert_2()
        await self.case_glitch_during_release()
        await self.case_short_assert_pulse()
        await self.case_clock_stop_during_reset()
        await self.case_clock_stop_during_release()
        await self.check_hooks_quiet("hooks_transparent", TP)

    async def case_async_assert_any_phase(self) -> None:
        name = "async_assert_any_phase"
        try:
            for phase in PHASES:
                await self._released()
                await self._phase_delay(phase)
                await self._assert_immediate(phase)
                sample_rst_sync(phase, "async_assert", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_sync_deassert_2(self) -> None:
        name = "sync_deassert_2_cycles"
        try:
            self.dut.rst_n.value = 0
            for _ in range(3):
                await RisingEdge(self.dut.core_clk)
            await RisingEdge(self.dut.core_clk)
            await wait_ps(100)
            self.dut.rst_n.value = 1
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("deassert is combo, not synced")
            await RisingEdge(self.dut.core_clk)
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("released after 1 edge (need 2)")
            await RisingEdge(self.dut.core_clk)
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 1:
                raise AssertionError("not released after 2 edges")
            sample_rst_sync("after_posedge", "sync_deassert_2", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_glitch_during_release(self) -> None:
        name = "glitch_during_release"
        try:
            self.dut.rst_n.value = 0
            for _ in range(2):
                await RisingEdge(self.dut.core_clk)
            await RisingEdge(self.dut.core_clk)
            await wait_ps(100)
            self.dut.rst_n.value = 1
            await RisingEdge(self.dut.core_clk)
            await wait_ps(100)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("partial release already 1")
            self.dut.rst_n.value = 0
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("glitch did not re-assert")
            await wait_ps(CORE_CLK_PERIOD_PS // 4)
            self.dut.rst_n.value = 1
            await RisingEdge(self.dut.core_clk)
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("glitch cleared in 1 edge")
            await RisingEdge(self.dut.core_clk)
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 1:
                raise AssertionError("did not recover 2 edges after glitch")
            sample_rst_sync("mid_high", "glitch", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_short_assert_pulse(self) -> None:
        name = "short_assert_pulse"
        try:
            await self._released()
            await RisingEdge(self.dut.core_clk)
            await wait_ps(CORE_CLK_PERIOD_PS // 4)
            self.dut.rst_n.value = 0
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("short pulse did not assert")
            await wait_ps(200)
            self.dut.rst_n.value = 1
            await RisingEdge(self.dut.core_clk)
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("short pulse released in 1 edge")
            await RisingEdge(self.dut.core_clk)
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 1:
                raise AssertionError("short pulse did not recover in 2 edges")
            sample_rst_sync("mid_high", "short_pulse", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_clock_stop_during_reset(self) -> None:
        name = "clock_stop_during_reset"
        try:
            self.dut.rst_n.value = 0
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("assert needs a clock (must be async)")
            await self.clkgen.stop()
            await wait_ps(CORE_CLK_PERIOD_PS * 5)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("released while clock stopped in reset")
            await self.clkgen.resume()
            for _ in range(2):
                await RisingEdge(self.dut.core_clk)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("clock restart released while rst_n=0")
            await RisingEdge(self.dut.core_clk)
            await wait_ps(100)
            self.dut.rst_n.value = 1
            await RisingEdge(self.dut.core_clk)
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("1 edge after clock-stop release")
            await RisingEdge(self.dut.core_clk)
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 1:
                raise AssertionError("need 2 edges after clock restart + release")
            sample_rst_sync("after_posedge", "clk_stop_rst", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_clock_stop_during_release(self) -> None:
        name = "clock_stop_during_release"
        try:
            self.dut.rst_n.value = 0
            for _ in range(2):
                await RisingEdge(self.dut.core_clk)
            await RisingEdge(self.dut.core_clk)
            await wait_ps(100)
            self.dut.rst_n.value = 1
            await RisingEdge(self.dut.core_clk)
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("released after first edge")
            await self.clkgen.stop()
            await wait_ps(CORE_CLK_PERIOD_PS * 4)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 0:
                raise AssertionError("finished release with clock stopped")
            await self.clkgen.resume()
            await RisingEdge(self.dut.core_clk)
            await wait_ps(20)
            if as_int(self.dut.rst_n_sync, "rst_n_sync") != 1:
                raise AssertionError("second edge after resume did not release")
            sample_rst_sync("after_posedge", "clk_stop_rel", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise


uvm_component_utils(RstSyncLeafTest)


@cocotb.test()
async def test_ub_rst_sync(dut):
    await leaf_entry(dut, "RstSyncLeafTest")
