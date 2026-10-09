"""RTL-free TB self-check. Proves the uvm-python skeleton on the passthrough harness."""

from __future__ import annotations

from pathlib import Path

import cocotb
from cocotb.triggers import RisingEdge
from uvm import (
    UVMConfigDb,
    UVMTest,
    UVM_LOW,
    run_test,
    uvm_component_utils,
    uvm_fatal,
    uvm_info,
)

from tb.vibe_uvm.coverage import export_functional, sample_selfcheck
from tb.vibe_uvm.env import UbEnv
from tb.vibe_uvm.items import CsrItem, VoItem, VrItem
from tb.vibe_uvm.seed_log import log_seed, resolve_seed

REPO = Path(__file__).resolve().parents[2]
REPORTS = REPO / "tb" / "reports"


class TbSelfcheckTest(UVMTest):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.env = UbEnv("env", self)
        self.dut = None
        self.hooks = 0

    def build_phase(self, phase):
        super().build_phase(phase)
        arr = []
        if UVMConfigDb.get(self, "", "vif", arr):
            self.dut = arr[0]
        else:
            uvm_fatal("TB", "vif not in config DB")
        self.env.bind(self.dut)
        self.hooks = 1 if self.env.hook.present else 0

    async def run_phase(self, phase):
        phase.raise_objection(self)
        dut = self.dut
        env = self.env
        env.clk_rst.start_clock()
        dut.vr_out_ready.value = 1
        await env.clk_rst.apply_reset()
        await env.hook.idle_inj()

        await self._check_valid_ready(env, dut)
        sample_selfcheck("vr", self.hooks)
        await self._check_valid_only(env, dut)
        sample_selfcheck("vo", self.hooks)
        await self._check_csr(env)
        sample_selfcheck("csr", self.hooks)
        await self._check_hooks(env)
        sample_selfcheck("hook", self.hooks)

        export_functional(REPORTS / "cov_func" / f"selfcheck_hooks{self.hooks}.json")
        uvm_info("TB", f"PASS tb_selfcheck TEST_HOOKS={self.hooks}", UVM_LOW)
        print(f"PASS tb_selfcheck TEST_HOOKS={self.hooks}", flush=True)
        phase.drop_objection(self)

    async def _check_valid_ready(self, env, dut):
        item = VrItem("vr")
        if not item.randomize():
            uvm_fatal("TB", "VrItem.randomize() failed")
        await env.vr.driver.drive_item(item)
        # 1-cycle registered slice: data appears on the next beat already consumed
        # Drive holds valid until ready; harness parks the beat on vr_out_*.
        timeout = 20
        while int(dut.vr_out_valid.value) != 1 and timeout:
            await RisingEdge(dut.core_clk)
            timeout -= 1
        if timeout == 0:
            uvm_fatal("TB", "valid/ready loopback never presented vr_out_valid")
        env.scoreboard.compare(item.data, int(dut.vr_out_data.value), "vr loopback")

    async def _check_valid_only(self, env, dut):
        item = VoItem("vo")
        if not item.randomize():
            uvm_fatal("TB", "VoItem.randomize() failed")
        await env.vo.driver.drive_item(item)
        await RisingEdge(dut.core_clk)
        timeout = 10
        while int(dut.vo_out_valid.value) != 1 and timeout:
            await RisingEdge(dut.core_clk)
            timeout -= 1
        env.scoreboard.compare(item.data, int(dut.vo_out_data.value), "vo loopback")

    async def _check_csr(self, env):
        wr = CsrItem("wr")
        wr.randomize()
        wr.write = 1
        wr.addr = 0x0000
        wr.wdata = 0x11223344
        await env.csr.driver.access(wr)
        env.scoreboard.compare(0, wr.err, "csr mapped write err")

        rd = CsrItem("rd")
        rd.write = 0
        rd.addr = 0x0000
        await env.csr.driver.access(rd)
        env.scoreboard.compare(0, rd.err, "csr mapped read err")
        env.scoreboard.compare(0x11223344, rd.rdata, "csr scratch readback")

        ro = CsrItem("ro")
        ro.write = 0
        ro.addr = 0x0004
        await env.csr.driver.access(ro)
        env.scoreboard.compare(0, ro.err, "csr ro err")
        env.scoreboard.compare(0xA5A50001, ro.rdata, "csr ro id")

        bad = CsrItem("bad")
        bad.write = 0
        bad.addr = 0x00F0
        await env.csr.driver.access(bad)
        env.scoreboard.compare(1, bad.err, "csr unmapped read sets csr_err")
        env.scoreboard.compare(0, bad.rdata, "csr unmapped read data")

        unal = CsrItem("unal")
        unal.write = 1
        unal.addr = 0x0001
        unal.wdata = 1
        await env.csr.driver.access(unal)
        env.scoreboard.compare(1, unal.err, "csr unaligned is unmapped")

        test = CsrItem("test")
        test.write = 0
        test.addr = 0x0300
        await env.csr.driver.access(test)
        env.scoreboard.compare(0, test.err, "TEST window is mapped (err=0)")
        # hooks0, or hooks1 with test_mode=0: read 0
        if not env.hook.present or env.hook.sample_obs().test_mode == 0:
            env.scoreboard.compare(0, test.rdata, "TEST window quiet when not live")

    async def _check_hooks(self, env):
        if not env.hook.present:
            uvm_info("TB", "TEST_HOOKS=0: no hook ports (SPEC §11 PRODUCT)", UVM_LOW)
            return
        await env.hook.set_test_mode(0)
        await env.hook.drive_inj(tb_inj_lid_bad=1, tb_inj_crd_cells=0x123, tb_inj_am_lock=5)
        obs = env.hook.sample_obs()
        env.scoreboard.compare(0, obs.obs["tb_obs_link_up"], "mode=0 obs held 0")
        env.scoreboard.compare(0, obs.obs["tb_obs_crd_cells"], "mode=0 crd obs 0")
        await env.hook.set_test_mode(1)
        await env.hook.drive_inj(tb_inj_lid_bad=1, tb_inj_crd_cells=0x123, tb_inj_am_lock=5)
        obs = env.hook.sample_obs()
        env.scoreboard.compare(1, obs.obs["tb_obs_link_up"], "mode=1 lid_bad visible")
        env.scoreboard.compare(0x123, obs.obs["tb_obs_crd_cells"], "mode=1 crd inj mux")
        await env.hook.idle_inj()


uvm_component_utils(TbSelfcheckTest)


@cocotb.test()
async def test_tb_skeleton(dut):
    seed = log_seed(resolve_seed())
    UVMConfigDb.set(None, "*", "vif", dut)
    if hasattr(dut, "vr_out_ready"):
        dut.vr_out_ready.value = 1
    await run_test("TbSelfcheckTest")
    # Keep seed in the log after UVM shuts down.
    print(f"SEED {seed}", flush=True)
