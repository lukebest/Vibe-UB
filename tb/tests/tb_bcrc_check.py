"""Leaf TB: ub_dll_bcrc_check (SPEC §2.6 / §7). CRC30-only compare; flag passthrough."""

from __future__ import annotations

import random

import cocotb
from cocotb.triggers import RisingEdge
from uvm import uvm_component_utils

from tb.vibe_uvm.bcrc_util import attach, extract_word, payload_flit
from tb.vibe_uvm.leaf_base import LeafUvmTest, as_int, leaf_entry, wait_ps
from tb.vibe_uvm.leaf_cov import sample_bcrc_check

TP = ["TP-UNIT-DLL-002"]


class BcrcCheckLeafTest(LeafUvmTest):
    TB_NAME = "ub_dll_bcrc_check"
    COV_PREFIX = "ub_dll_bcrc_check"

    async def _reset_dut(self) -> None:
        self.dut.start.value = 0
        self.dut.valid_in.value = 0
        self.dut.last.value = 0
        self.dut.data_in.value = 0
        self.dut.crc_recv.value = 0
        self.dut.rst_n.value = 0
        for _ in range(3):
            await RisingEdge(self.dut.core_clk)
        self.dut.rst_n.value = 1
        await RisingEdge(self.dut.core_clk)

    async def _feed(self, flits: list[int], crc_recv: int | None = None) -> dict:
        self.dut.start.value = 1
        self.dut.valid_in.value = 0
        self.dut.last.value = 0
        await RisingEdge(self.dut.core_clk)
        self.dut.start.value = 0
        recv = extract_word(flits[-1]) if crc_recv is None else crc_recv
        for i, flit in enumerate(flits):
            last = i == len(flits) - 1
            self.dut.valid_in.value = 1
            self.dut.data_in.value = flit
            self.dut.last.value = int(last)
            if last:
                self.dut.crc_recv.value = recv
            await RisingEdge(self.dut.core_clk)
        self.dut.valid_in.value = 0
        self.dut.last.value = 0
        return {
            "done": as_int(self.dut.done, "done"),
            "ok": as_int(self.dut.crc_ok, "crc_ok"),
            "fail": as_int(self.dut.crc_fail, "crc_fail"),
            "eflag": as_int(self.dut.error_flag_rx, "error_flag_rx"),
            "word": as_int(self.dut.crc_word, "crc_word"),
            "recv": recv,
        }

    async def run_cases(self) -> None:
        await self._reset_dut()
        await self.case_reset_quiet()
        await self.case_good()
        await self.case_flag_flip()
        await self.case_rsvd_flip()
        await self.case_single_bit()
        await self.case_random()
        await self.case_latency_1()
        await self.check_hooks_quiet("hooks_transparent", TP)

    async def case_reset_quiet(self) -> None:
        name = "reset_quiet"
        try:
            self.dut.rst_n.value = 0
            await RisingEdge(self.dut.core_clk)
            for sig in ("done", "crc_ok", "crc_fail", "error_flag_rx"):
                if as_int(getattr(self.dut, sig), sig) != 0:
                    raise AssertionError(f"{sig} != 0 in reset")
            self.dut.rst_n.value = 1
            await RisingEdge(self.dut.core_clk)
            sample_bcrc_check("rst_quiet", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_good(self) -> None:
        name = "good_packet"
        try:
            attached = attach([payload_flit(list(range(16)))])
            r = await self._feed(attached)
            if r["done"] != 1 or r["ok"] != 1 or r["fail"] != 0:
                raise AssertionError(f"good {r}")
            if r["eflag"] != 0:
                raise AssertionError(f"eflag {r['eflag']}")
            sample_bcrc_check("good", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_flag_flip(self) -> None:
        name = "flip_error_flag"
        try:
            raw = [payload_flit(list(range(16)))]
            a = attach(raw, error_flag=0)
            b = attach(raw, error_flag=1)
            ra = await self._feed(a)
            rb = await self._feed(b)
            if ra["ok"] != rb["ok"] or ra["fail"] != rb["fail"]:
                raise AssertionError(f"CRC result changed: {ra} vs {rb}")
            if ra["ok"] != 1 or ra["fail"] != 0:
                raise AssertionError(f"good CRC failed: {ra}")
            if ra["eflag"] != 0 or rb["eflag"] != 1:
                raise AssertionError(
                    f"error_flag_rx did not follow crc_recv[30]: {ra['eflag']}/{rb['eflag']}"
                )
            sample_bcrc_check("flag_flip", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_rsvd_flip(self) -> None:
        name = "flip_rsvd"
        try:
            raw = [payload_flit([0xA5] * 16)]
            base = attach(raw, error_flag=0, reserved=0)
            rsvd = attach(raw, error_flag=0, reserved=1)
            both = attach(raw, error_flag=1, reserved=1)
            r0 = await self._feed(base)
            r1 = await self._feed(rsvd)
            r2 = await self._feed(both)
            if r0["ok"] != 1 or r1["ok"] != 1 or r2["ok"] != 1:
                raise AssertionError(f"rsvd affected CRC: {r0}/{r1}/{r2}")
            if r0["eflag"] != 0 or r1["eflag"] != 0:
                raise AssertionError("rsvd leaked into error_flag_rx")
            if r2["eflag"] != 1:
                raise AssertionError("flag lost when rsvd=1")
            sample_bcrc_check("rsvd_flip", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_single_bit(self) -> None:
        name = "any_single_bit_detected"
        try:
            raw = [payload_flit([0x00] * 16)]
            good = attach(raw)
            # Payload bits (bytes 0–15) and CRC30 bits. Skip flag/rsvd (30/31).
            bits = list(range(16 * 8)) + list(range(16 * 8, 16 * 8 + 30))
            for bit in bits:
                mutated = [good[0] ^ (1 << bit)]
                r = await self._feed(mutated)
                if r["fail"] != 1 or r["ok"] != 0:
                    raise AssertionError(f"bit {bit} not detected: {r}")
            sample_bcrc_check("bit_flip", self.hooks)
            self.rec.pass_(name, TP, f"flips={len(bits)}")
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_random(self) -> None:
        name = "random"
        try:
            rng = random.Random(self.seed)
            for n_flit in (1, 2):
                raw = [rng.randrange(1 << 160) for _ in range(n_flit)]
                good = attach(raw)
                r = await self._feed(good)
                if r["ok"] != 1 or r["fail"] != 0:
                    raise AssertionError(f"good n={n_flit} {r}")
                bad = list(good)
                bad[-1] ^= 1
                r2 = await self._feed(bad)
                if r2["fail"] != 1 or r2["ok"] != 0:
                    raise AssertionError(f"rand flip missed n={n_flit} {r2}")
            sample_bcrc_check("rand", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_latency_1(self) -> None:
        name = "latency_1cycle_flag_align"
        try:
            raw = [payload_flit(list(range(16)))]
            flits = attach(raw, error_flag=1)
            self.dut.start.value = 1
            self.dut.valid_in.value = 0
            await RisingEdge(self.dut.core_clk)
            self.dut.start.value = 0
            self.dut.valid_in.value = 1
            self.dut.last.value = 1
            self.dut.data_in.value = flits[0]
            self.dut.crc_recv.value = extract_word(flits[0])
            # Same cycle as last: outputs still previous (0 after start).
            await wait_ps(20)
            pre_done = as_int(self.dut.done, "done")
            await RisingEdge(self.dut.core_clk)
            if pre_done != 0:
                raise AssertionError("done on the last input beat (0-cycle, expected 1)")
            if as_int(self.dut.done, "done") != 1:
                raise AssertionError("done not 1 cycle after last")
            if as_int(self.dut.error_flag_rx, "error_flag_rx") != 1:
                raise AssertionError("error_flag_rx not aligned with done")
            if as_int(self.dut.crc_ok, "crc_ok") != 1:
                raise AssertionError("crc_ok not aligned with done")
            sample_bcrc_check("lat1", self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise


uvm_component_utils(BcrcCheckLeafTest)


@cocotb.test()
async def test_ub_bcrc_check(dut):
    await leaf_entry(dut, "BcrcCheckLeafTest")
