"""Leaf TB: dist→dedist collect. Dist and dedist are scored independently."""

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
    unpack_symbols,
    walking_ones,
)

TP = ["TP-UNIT-PCS-008"]


class LaneCollectLeafTest(LeafUvmTest):
    TB_NAME = "ub_pcs_lane_collect"
    COV_PREFIX = "ub_pcs_lane_collect"

    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.num_lanes = env_int("NUM_LANES", 4)
        self.width = self.num_lanes * PMA_W

    async def _drive(self, data: int, valid: int = 1) -> tuple[int, int, int]:
        self.dut.data_in.value = data
        self.dut.valid_in.value = valid
        await wait_ps(20)
        return (
            as_int(self.dut.data_mid, "data_mid"),
            as_int(self.dut.data_out, "data_out"),
            as_int(self.dut.valid_out, "valid_out"),
        )

    async def run_cases(self) -> None:
        self.dut.data_in.value = 0
        self.dut.valid_in.value = 0
        self.dut.rst_n.value = 0
        await wait_ps(20)
        await self.case_valid_out_in_reset()
        self.dut.rst_n.value = 1
        await wait_ps(20)
        await self.case_inc_symbols()
        await self.case_onehot_symbols()
        await self.case_loopback()
        await self.case_corners()
        await self.case_random()

    def _score_pair(self, mid: int, out: int, symbols: list[int], ctx: str) -> None:
        exp_mid = expected_window(symbols, self.num_lanes)
        self.check_word(mid, exp_mid, self.num_lanes, f"{ctx} dist")
        self.check_word(out, pack_symbols(symbols), self.num_lanes, f"{ctx} collect")
        self.check_word(
            out, expected_dedist(mid, self.num_lanes), self.num_lanes, f"{ctx} dedist"
        )

    async def case_valid_out_in_reset(self) -> None:
        name = "valid_out_0_in_reset"
        try:
            _, _, vout = await self._drive(1, 1)
            self.check(0, vout, "valid_out in reset")
            sample_lane(self.num_lanes, "valid_rst", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_inc_symbols(self) -> None:
        name = "inc_symbols_mapping"
        try:
            symbols = incrementing_symbols(self.num_lanes)
            mid, out, vout = await self._drive(pack_symbols(symbols), 1)
            self.check(1, vout, "inc valid")
            self._score_pair(mid, out, symbols, "inc_symbols")
            sample_lane(self.num_lanes, "inc", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_onehot_symbols(self) -> None:
        name = "onehot_symbol_scan"
        try:
            for idx, symbols in onehot_symbols(self.num_lanes):
                mid, out, _ = await self._drive(pack_symbols(symbols), 1)
                self._score_pair(mid, out, symbols, f"onehot ca[{idx}]")
            sample_lane(self.num_lanes, "onehot", self.hooks)
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
                mid, out, vout = await self._drive(pack_symbols(symbols), 1)
                self.check(1, vout, "loopback valid")
                self._score_pair(mid, out, symbols, "loopback")
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
                symbols = unpack_symbols(vec, self.num_lanes)
                mid, out, _ = await self._drive(vec, 1)
                self._score_pair(mid, out, symbols, f"0x{vec:x}")
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
                symbols = unpack_symbols(vec, self.num_lanes)
                mid, out, _ = await self._drive(vec, 1)
                self._score_pair(mid, out, symbols, "rand")
            sample_lane(self.num_lanes, "rand", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise


uvm_component_utils(LaneCollectLeafTest)


@cocotb.test()
async def test_ub_lane_collect(dut):
    await leaf_entry(dut, "LaneCollectLeafTest")
