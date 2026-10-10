"""Leaf TB: dist→dedist collect loopback (SPEC §2.4; UB-PHY §3.2.3.3)."""

from __future__ import annotations

import random

import cocotb
from uvm import uvm_component_utils

from tb.vibe_uvm.leaf_base import LeafUvmTest, as_int, env_int, leaf_entry, wait_ps
from tb.vibe_uvm.leaf_cov import sample_lane
from tb.vibe_uvm.lane_util import PMA_W, nsym, pack_symbols, walking_ones

TP = ["TP-UNIT-PCS-008"]


class LaneCollectLeafTest(LeafUvmTest):
    TB_NAME = "ub_pcs_lane_collect"
    COV_PREFIX = "ub_pcs_lane_collect"

    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.num_lanes = env_int("NUM_LANES", 4)
        self.width = self.num_lanes * PMA_W

    async def _drive(self, data: int, valid: int = 1) -> tuple[int, int]:
        self.dut.data_in.value = data
        self.dut.valid_in.value = valid
        await wait_ps(20)
        return as_int(self.dut.data_out, "data_out"), as_int(self.dut.valid_out, "valid_out")

    async def run_cases(self) -> None:
        self.dut.data_in.value = 0
        self.dut.valid_in.value = 0
        self.dut.rst_n.value = 0
        await wait_ps(20)
        await self.case_valid_out_in_reset()
        self.dut.rst_n.value = 1
        await wait_ps(20)
        await self.case_loopback()
        await self.case_corners()
        await self.case_random()

    async def case_valid_out_in_reset(self) -> None:
        name = "valid_out_0_in_reset"
        try:
            _, vout = await self._drive(1, 1)
            if vout != 0:
                raise AssertionError(f"valid_out={vout} in reset")
            sample_lane(self.num_lanes, "valid_rst", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_loopback(self) -> None:
        name = "dist_dedist_restore"
        try:
            ns = nsym(self.num_lanes)
            for symbols in (
                list(range(ns)),
                [0] * ns,
                [0xFF] * ns,
                [(i * 17 + self.num_lanes) & 0xFF for i in range(ns)],
            ):
                vec = pack_symbols(symbols)
                got, vout = await self._drive(vec, 1)
                if vout != 1 or got != vec:
                    raise AssertionError(f"restore failed valid={vout} got=0x{got:x}")
            sample_lane(self.num_lanes, "loopback", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_corners(self) -> None:
        name = "walk_and_full"
        try:
            mask = (1 << self.width) - 1
            for vec in (0, mask, *walking_ones(self.width)):
                got, _ = await self._drive(vec, 1)
                if got != vec:
                    raise AssertionError(f"0x{vec:x} -> 0x{got:x}")
            sample_lane(self.num_lanes, "walk", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_random(self) -> None:
        name = "random"
        try:
            rng = random.Random(self.seed)
            for _ in range(16):
                vec = rng.randrange(1 << self.width)
                got, _ = await self._drive(vec, 1)
                if got != vec:
                    raise AssertionError(f"rand 0x{vec:x} -> 0x{got:x}")
            sample_lane(self.num_lanes, "rand", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise


uvm_component_utils(LaneCollectLeafTest)


@cocotb.test()
async def test_ub_lane_collect(dut):
    await leaf_entry(dut, "LaneCollectLeafTest")
