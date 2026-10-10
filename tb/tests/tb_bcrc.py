"""Leaf TB: ub_dll_bcrc (SPEC §2.6 / §7). TX ERROR_FLAG hardwired 0."""

from __future__ import annotations

import random

import cocotb
from cocotb.triggers import RisingEdge
from uvm import uvm_component_utils

from tb.vibe_uvm.bcrc_util import attach, crc30_of, pack_word, payload_flit
from tb.vibe_uvm.leaf_base import LeafUvmTest, as_int, leaf_entry, wait_ps
from tb.vibe_uvm.leaf_cov import sample_bcrc

TP = ["TP-UNIT-DLL-001"]


class BcrcLeafTest(LeafUvmTest):
    TB_NAME = "ub_dll_bcrc"
    COV_PREFIX = "ub_dll_bcrc"

    async def _reset_dut(self) -> None:
        self.dut.start.value = 0
        self.dut.valid_in.value = 0
        self.dut.last.value = 0
        self.dut.data_in.value = 0
        self.dut.rst_n.value = 0
        for _ in range(3):
            await RisingEdge(self.dut.core_clk)
        self.dut.rst_n.value = 1
        await RisingEdge(self.dut.core_clk)

    async def _feed(self, flits: list[int]) -> tuple[int, int]:
        self.dut.start.value = 1
        self.dut.valid_in.value = 0
        self.dut.last.value = 0
        await RisingEdge(self.dut.core_clk)
        self.dut.start.value = 0
        for i, flit in enumerate(flits):
            self.dut.valid_in.value = 1
            self.dut.data_in.value = flit
            self.dut.last.value = int(i == len(flits) - 1)
            await RisingEdge(self.dut.core_clk)
            await wait_ps(1)
        self.dut.valid_in.value = 0
        self.dut.last.value = 0
        done = as_int(self.dut.done, "done")
        word = as_int(self.dut.crc_word, "crc_word")
        return done, word

    async def run_cases(self) -> None:
        await self._reset_dut()
        await self.case_reset_quiet()
        await self.case_directed()
        await self.case_two_flit()
        await self.case_random()
        await self.case_tx_flag0()
        await self.case_start_reinit()
        await self.check_hooks_quiet("hooks_transparent", TP)

    async def case_reset_quiet(self) -> None:
        name = "reset_quiet"
        try:
            self.dut.rst_n.value = 0
            await RisingEdge(self.dut.core_clk)
            if as_int(self.dut.done, "done") != 0:
                raise AssertionError("done != 0 in reset")
            if as_int(self.dut.crc_word, "crc_word") != 0:
                raise AssertionError("crc_word != 0 in reset")
            self.dut.rst_n.value = 1
            await RisingEdge(self.dut.core_clk)
            sample_bcrc("rst_quiet", 1, self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_directed(self) -> None:
        vectors = (
            ("dir0", [0x00] * 16),
            ("dir1", [0xFF] * 16),
            ("dir_inc", list(range(16))),
        )
        try:
            for kind, payload in vectors:
                raw = [payload_flit(payload)]
                attached = attach(raw)
                done, word = await self._feed(attached)
                exp = pack_word(crc30_of(raw), 0, 0)
                if done != 1:
                    raise AssertionError(f"{kind}: done={done}")
                if word != exp:
                    raise AssertionError(
                        f"{kind}: crc_word=0x{word:08x} expected 0x{exp:08x}"
                    )
                sample_bcrc(kind, 1, self.hooks)
                self.rec.pass_(f"directed_{kind}", TP)
        except Exception as exc:
            self.rec.fail("directed", TP, str(exc))
            raise

    async def case_two_flit(self) -> None:
        name = "two_flit"
        try:
            from tb.vibe_uvm.golden import bcrc as BM

            first = BM.bytes_to_flit(list(range(20)))
            second = payload_flit([0xA5] * 16)
            raw = [first, second]
            attached = attach(raw)
            done, word = await self._feed(attached)
            exp = pack_word(crc30_of(raw), 0, 0)
            if done != 1 or word != exp:
                raise AssertionError(f"done={done} word=0x{word:08x} exp=0x{exp:08x}")
            sample_bcrc("two_flit", 2, self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_random(self) -> None:
        name = "random"
        try:
            rng = random.Random(self.seed)
            for n_flit in (1, 2, 3):
                raw = [rng.randrange(1 << 160) for _ in range(n_flit)]
                attached = attach(raw)
                done, word = await self._feed(attached)
                exp = pack_word(crc30_of(raw), 0, 0)
                if done != 1 or word != exp:
                    raise AssertionError(
                        f"n={n_flit} done={done} word=0x{word:08x} exp=0x{exp:08x}"
                    )
                sample_bcrc("rand", n_flit, self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_tx_flag0(self) -> None:
        name = "tx_error_flag_hardwired_0"
        try:
            raw = [payload_flit(list(range(16)))]
            done, word = await self._feed(attach(raw, error_flag=1))
            if done != 1:
                raise AssertionError("done=0")
            if (word >> 30) & 1:
                raise AssertionError(f"TX ERROR_FLAG set: 0x{word:08x}")
            if (word >> 31) & 1:
                raise AssertionError(f"TX rsvd set: 0x{word:08x}")
            if (word & 0x3FFFFFFF) != crc30_of(raw):
                raise AssertionError("CRC30 field mismatch")
            sample_bcrc("tx_flag0", 1, self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_start_reinit(self) -> None:
        name = "start_reinit"
        try:
            a = attach([payload_flit([0x00] * 16)])
            b = attach([payload_flit([0xFF] * 16)])
            await self._feed(a)
            done, word = await self._feed(b)
            exp = pack_word(crc30_of([payload_flit([0xFF] * 16)]), 0, 0)
            if done != 1 or word != exp:
                raise AssertionError("start did not re-init between blocks")
            sample_bcrc("start_reinit", 1, self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise


uvm_component_utils(BcrcLeafTest)


@cocotb.test()
async def test_ub_bcrc(dut):
    await leaf_entry(dut, "BcrcLeafTest")
