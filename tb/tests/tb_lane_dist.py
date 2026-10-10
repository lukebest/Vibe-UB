"""Leaf TB: ub_pcs_lane_dist (SPEC §2.4 / §3.3; UB-PHY §3.2.2.3 / §3.2.5)."""

from __future__ import annotations

import random

import cocotb
from uvm import uvm_component_utils

from tb.vibe_uvm.leaf_base import LeafUvmTest, as_int, env_int, leaf_entry, wait_ps
from tb.vibe_uvm.leaf_cov import sample_lane
from tb.vibe_uvm.lane_util import (
    PMA_W,
    compare_word,
    expected_window,
    incrementing_symbols,
    nsym,
    onehot_symbols,
    pack_symbols,
    rs128_high_windows,
    unpack_lane_first_symbols,
    walking_ones,
)

TP_X4 = ["TP-UNIT-PCS-006"]
TP_W = ["TP-UNIT-PCS-007"]
TP_ALL = ["TP-UNIT-PCS-006", "TP-UNIT-PCS-007"]


class LaneDistLeafTest(LeafUvmTest):
    TB_NAME = "ub_pcs_lane_dist"
    COV_PREFIX = "ub_pcs_lane_dist"

    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.num_lanes = env_int("NUM_LANES", 4)
        self.width = self.num_lanes * PMA_W

    async def _idle_inputs(self) -> None:
        self.dut.data_in.value = 0
        self.dut.valid_in.value = 0
        self.dut.rst_n.value = 0
        await wait_ps(20)

    async def _out_reset(self) -> None:
        self.dut.rst_n.value = 1
        await wait_ps(20)

    async def _drive(self, data: int, valid: int = 1) -> tuple[int, int]:
        self.dut.data_in.value = data
        self.dut.valid_in.value = valid
        await wait_ps(20)
        return as_int(self.dut.data_out, "data_out"), as_int(self.dut.valid_out, "valid_out")

    async def run_cases(self) -> None:
        await self._idle_inputs()
        await self.case_valid_out_in_reset()
        await self._out_reset()
        if self.num_lanes == 4:
            await self.case_x4_first_on_wire()
        await self.case_inc_symbols()
        await self.case_onehot_symbols()
        await self.case_window_vs_golden()
        await self.case_all_zero()
        await self.case_all_one()
        await self.case_walking_one()
        await self.case_random()
        await self.case_latency_0()

    async def case_valid_out_in_reset(self) -> None:
        name = "valid_out_0_in_reset"
        tps = TP_X4 if self.num_lanes == 4 else TP_W
        try:
            self.dut.rst_n.value = 0
            dout, vout = await self._drive(0xA5A5A5A5, valid=1)
            if vout != 0:
                raise AssertionError(f"valid_out={vout} in reset")
            sample_lane(self.num_lanes, "valid_rst", self.hooks)
            self.rec.pass_(name, tps)
        except Exception as exc:
            self.rec.fail(name, tps, str(exc))
            raise

    async def case_x4_first_on_wire(self) -> None:
        name = "x4_first_on_wire_127_126_125_124"
        try:
            rows = rs128_high_windows(4)
            window, exp = rows[0]
            got, vout = await self._drive(pack_symbols(window), 1)
            if vout != 1:
                raise AssertionError(f"valid_out={vout}")
            first = unpack_lane_first_symbols(got, 4)
            if first != [127, 126, 125, 124]:
                raise AssertionError(f"first-on-wire {first} expected [127,126,125,124]")
            compare_word(got, exp, 4, "beat0")
            for k, (win, exp_k) in enumerate(rows[1:], start=1):
                got_k, _ = await self._drive(pack_symbols(win), 1)
                compare_word(got_k, exp_k, 4, f"RS128 word {k}")
            sample_lane(4, "first_wire", self.hooks)
            self.rec.pass_(name, TP_X4)
        except Exception as exc:
            self.rec.fail(name, TP_X4, str(exc))
            raise

    async def case_window_vs_golden(self) -> None:
        name = "window_vs_golden"
        tps = TP_X4 if self.num_lanes == 4 else TP_W
        try:
            ns = nsym(self.num_lanes)
            rng = random.Random(self.seed ^ (self.num_lanes << 8))
            symbols = [rng.randrange(256) for _ in range(ns)]
            exp = expected_window(symbols, self.num_lanes)
            got, _ = await self._drive(pack_symbols(symbols), 1)
            compare_word(got, exp, self.num_lanes, "window")
            sample_lane(self.num_lanes, "window", self.hooks)
            self.rec.pass_(name, tps)
        except Exception as exc:
            self.rec.fail(name, tps, str(exc))
            raise

    async def case_all_zero(self) -> None:
        name = "all_zero"
        tps = TP_X4 if self.num_lanes == 4 else TP_W
        try:
            ns = nsym(self.num_lanes)
            exp = expected_window([0] * ns, self.num_lanes)
            got, _ = await self._drive(0, 1)
            compare_word(got, exp, self.num_lanes, "zero")
            sample_lane(self.num_lanes, "zero", self.hooks)
            self.rec.pass_(name, tps)
        except Exception as exc:
            self.rec.fail(name, tps, str(exc))
            raise

    async def case_all_one(self) -> None:
        name = "all_one"
        tps = TP_X4 if self.num_lanes == 4 else TP_W
        try:
            ns = nsym(self.num_lanes)
            ones = (1 << self.width) - 1
            exp = expected_window([0xFF] * ns, self.num_lanes)
            got, _ = await self._drive(ones, 1)
            compare_word(got, exp, self.num_lanes, "one")
            sample_lane(self.num_lanes, "one", self.hooks)
            self.rec.pass_(name, tps)
        except Exception as exc:
            self.rec.fail(name, tps, str(exc))
            raise

    async def case_walking_one(self) -> None:
        name = "walking_one"
        tps = TP_X4 if self.num_lanes == 4 else TP_W
        try:
            ns = nsym(self.num_lanes)
            for vec in walking_ones(self.width):
                symbols = [(vec >> (8 * i)) & 0xFF for i in range(ns)]
                exp = expected_window(symbols, self.num_lanes)
                got, _ = await self._drive(vec, 1)
                compare_word(got, exp, self.num_lanes, f"walk 0x{vec:x}")
            sample_lane(self.num_lanes, "walk", self.hooks)
            self.rec.pass_(name, tps)
        except Exception as exc:
            self.rec.fail(name, tps, str(exc))
            raise

    async def case_random(self) -> None:
        name = "random"
        tps = TP_X4 if self.num_lanes == 4 else TP_W
        try:
            rng = random.Random(self.seed)
            ns = nsym(self.num_lanes)
            for _ in range(16):
                symbols = [rng.randrange(256) for _ in range(ns)]
                exp = expected_window(symbols, self.num_lanes)
                got, vout = await self._drive(pack_symbols(symbols), 1)
                if vout != 1:
                    raise AssertionError(f"rand valid={vout}")
                compare_word(got, exp, self.num_lanes, "rand")
            sample_lane(self.num_lanes, "rand", self.hooks)
            self.rec.pass_(name, tps)
        except Exception as exc:
            self.rec.fail(name, tps, str(exc))
            raise

    async def case_latency_0(self) -> None:
        name = "latency_0cycle"
        tps = TP_X4 if self.num_lanes == 4 else TP_W
        try:
            a = expected_window([1] * nsym(self.num_lanes), self.num_lanes)
            b = expected_window([2] * nsym(self.num_lanes), self.num_lanes)
            got_a, _ = await self._drive(pack_symbols([1] * nsym(self.num_lanes)), 1)
            got_b, _ = await self._drive(pack_symbols([2] * nsym(self.num_lanes)), 1)
            compare_word(got_a, a, self.num_lanes, "lat0 a")
            compare_word(got_b, b, self.num_lanes, "lat0 b")
            sample_lane(self.num_lanes, "lat0", self.hooks)
            self.rec.pass_(name, tps)
        except Exception as exc:
            self.rec.fail(name, tps, str(exc))
            raise

    async def case_inc_symbols(self) -> None:
        name = "inc_symbols_mapping"
        tps = TP_X4 if self.num_lanes == 4 else TP_W
        try:
            symbols = incrementing_symbols(self.num_lanes)
            exp = expected_window(symbols, self.num_lanes)
            got, vout = await self._drive(pack_symbols(symbols), 1)
            if vout != 1:
                raise AssertionError(f"valid_out={vout}")
            compare_word(got, exp, self.num_lanes, "inc_symbols")
            sample_lane(self.num_lanes, "inc", self.hooks)
            self.rec.pass_(name, tps)
        except Exception as exc:
            self.rec.fail(name, tps, str(exc))
            raise

    async def case_onehot_symbols(self) -> None:
        name = "onehot_symbol_scan"
        tps = TP_X4 if self.num_lanes == 4 else TP_W
        try:
            for idx, symbols in onehot_symbols(self.num_lanes):
                exp = expected_window(symbols, self.num_lanes)
                got, _ = await self._drive(pack_symbols(symbols), 1)
                compare_word(got, exp, self.num_lanes, f"onehot ca[{idx}]")
            sample_lane(self.num_lanes, "onehot", self.hooks)
            self.rec.pass_(name, tps)
        except Exception as exc:
            self.rec.fail(name, tps, str(exc))
            raise


uvm_component_utils(LaneDistLeafTest)


@cocotb.test()
async def test_ub_lane_dist(dut):
    await leaf_entry(dut, "LaneDistLeafTest")
