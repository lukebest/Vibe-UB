"""Leaf TB: ub_pcs_lane_dedist (SPEC §2.4 / §3.3; UB-PHY §3.2.3.3)."""

from __future__ import annotations

import random

import cocotb
from uvm import uvm_component_utils

from tb.vibe_uvm.leaf_base import LeafUvmTest, as_int, env_int, leaf_entry, wait_ps
from tb.vibe_uvm.leaf_cov import sample_lane
from tb.vibe_uvm.lane_util import (
    PMA_W,
    expected_dedist,
    expected_window,
    incrementing_symbols,
    nsym,
    onehot_symbols,
    pack_symbols,
    walking_ones,
)

TP = ["TP-UNIT-PCS-008"]


class LaneDedistLeafTest(LeafUvmTest):
    TB_NAME = "ub_pcs_lane_dedist"
    COV_PREFIX = "ub_pcs_lane_dedist"

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
        await self.case_inverse()
        await self.case_inc_symbols()
        await self.case_onehot_symbols()
        await self.case_corners()
        await self.case_walking_one()
        await self.case_random()
        await self.case_latency_0()

    async def case_valid_out_in_reset(self) -> None:
        name = "valid_out_0_in_reset"
        try:
            _, vout = await self._drive(1, 1)
            self.check(0, vout, "valid_out in reset")
            sample_lane(self.num_lanes, "valid_rst", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_inverse(self) -> None:
        name = "inverse_of_dist"
        try:
            ns = nsym(self.num_lanes)
            symbols = list(range(ns))
            striped = expected_window(symbols, self.num_lanes)
            got, vout = await self._drive(striped, 1)
            exp = pack_symbols(symbols)
            self.check(1, vout, "inverse valid")
            self.check_word(got, exp, self.num_lanes, "inverse")
            sample_lane(self.num_lanes, "window", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_corners(self) -> None:
        name = "corners_zero_one"
        try:
            for label, vec in (("zero", 0), ("one", (1 << self.width) - 1)):
                exp = expected_dedist(vec, self.num_lanes)
                got, _ = await self._drive(vec, 1)
                self.check_word(got, exp, self.num_lanes, label)
                sample_lane(self.num_lanes, label, self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_walking_one(self) -> None:
        name = "walking_one"
        try:
            for vec in walking_ones(self.width):
                exp = expected_dedist(vec, self.num_lanes)
                got, _ = await self._drive(vec, 1)
                self.check_word(got, exp, self.num_lanes, f"walk 0x{vec:x}")
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
                exp = expected_dedist(vec, self.num_lanes)
                got, _ = await self._drive(vec, 1)
                self.check_word(got, exp, self.num_lanes, "rand")
            sample_lane(self.num_lanes, "rand", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_latency_0(self) -> None:
        name = "latency_0cycle"
        try:
            a = expected_dedist(1, self.num_lanes)
            b = expected_dedist(2, self.num_lanes)
            got_a, _ = await self._drive(1, 1)
            got_b, _ = await self._drive(2, 1)
            self.check_word(got_a, a, self.num_lanes, "lat0 a")
            self.check_word(got_b, b, self.num_lanes, "lat0 b")
            sample_lane(self.num_lanes, "lat0", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_inc_symbols(self) -> None:
        name = "inc_symbols_mapping"
        try:
            symbols = incrementing_symbols(self.num_lanes)
            striped = expected_window(symbols, self.num_lanes)
            got, vout = await self._drive(striped, 1)
            self.check(1, vout, "inc valid")
            self.check_word(got, pack_symbols(symbols), self.num_lanes, "inc_symbols")
            sample_lane(self.num_lanes, "inc", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_onehot_symbols(self) -> None:
        name = "onehot_symbol_scan"
        try:
            for idx, symbols in onehot_symbols(self.num_lanes):
                striped = expected_window(symbols, self.num_lanes)
                got, _ = await self._drive(striped, 1)
                self.check_word(got, pack_symbols(symbols), self.num_lanes, f"onehot ca[{idx}]")
            sample_lane(self.num_lanes, "onehot", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise


uvm_component_utils(LaneDedistLeafTest)


@cocotb.test()
async def test_ub_lane_dedist(dut):
    await leaf_entry(dut, "LaneDedistLeafTest")
