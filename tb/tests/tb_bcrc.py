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

    async def _beat(self, *, start: int = 0, valid: int = 0, last: int = 0, data: int = 0) -> None:
        self.dut.start.value = start
        self.dut.valid_in.value = valid
        self.dut.last.value = last
        self.dut.data_in.value = data
        await RisingEdge(self.dut.core_clk)
        await wait_ps(1)

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
        await self.case_onehot()
        await self.case_two_flit()
        await self.case_random()
        await self.case_tx_flag0()
        await self.case_start_reinit()
        await self.case_xia_start_valid()
        await self.case_xia_start_valid_last()
        await self.case_xia_start_only()
        await self.case_xia_start_mid_restart()

    async def case_reset_quiet(self) -> None:
        name = "reset_quiet"
        try:
            self.dut.rst_n.value = 0
            await RisingEdge(self.dut.core_clk)
            self.check(0, as_int(self.dut.done, "done"), "done in reset")
            self.check(0, as_int(self.dut.crc_word, "crc_word"), "crc_word in reset")
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
                self.check(1, done, f"{kind} done")
                self.check(exp, word, f"{kind} crc_word")
                sample_bcrc(kind, 1, self.hooks)
                self.rec.pass_(f"directed_{kind}", TP)
        except Exception as exc:
            self.rec.fail("directed", TP, str(exc))
            raise

    async def case_onehot(self) -> None:
        name = "onehot_payload_bits"
        try:
            for bit in range(16 * 8):
                payload = [0] * 16
                payload[bit // 8] = 1 << (bit % 8)
                raw = [payload_flit(payload)]
                attached = attach(raw)
                done, word = await self._feed(attached)
                exp = pack_word(crc30_of(raw), 0, 0)
                self.check(1, done, f"onehot {bit} done")
                self.check(exp, word, f"onehot {bit} crc_word")
            sample_bcrc("onehot", 1, self.hooks)
            self.rec.pass_(name, TP, f"bits={16 * 8}")
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
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
            self.check(1, done, "two_flit done")
            self.check(exp, word, "two_flit crc_word")
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
                self.check(1, done, f"rand n={n_flit} done")
                self.check(exp, word, f"rand n={n_flit} crc_word")
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
            self.check(1, done, "tx_flag0 done")
            self.check(0, (word >> 30) & 1, "TX ERROR_FLAG")
            self.check(0, (word >> 31) & 1, "TX rsvd")
            self.check(crc30_of(raw), word & 0x3FFFFFFF, "CRC30 field")
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
            self.check(1, done, "reinit done")
            self.check(exp, word, "reinit crc_word")
            sample_bcrc("start_reinit", 1, self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_xia_start_valid(self) -> None:
        """Xia §2.6: start&&valid same cycle folds that flit from INIT."""
        name = "xia_start_valid"
        try:
            from tb.vibe_uvm.golden import bcrc as BM

            first = BM.bytes_to_flit(list(range(20)))
            second = payload_flit([0x5A] * 16)
            raw = [first, second]
            attached = attach(raw)
            model = BM.UbDllBcrc()
            model.start()
            model.eat(attached[0], last=False)
            exp30 = model.eat(attached[1], last=True)
            await self._beat(start=1, valid=1, last=0, data=attached[0])
            await self._beat(start=0, valid=1, last=1, data=attached[1])
            self.check(1, as_int(self.dut.done, "done"), "xia start+valid done")
            self.check(pack_word(exp30, 0, 0), as_int(self.dut.crc_word, "crc_word"),
                       "xia start+valid crc_word")
            sample_bcrc("xia_start_valid", 2, self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_xia_start_valid_last(self) -> None:
        """Xia §2.6: start&&valid&&last = model eat(flit, last=True)."""
        name = "xia_start_valid_last"
        try:
            from tb.vibe_uvm.golden import bcrc as BM

            raw = [payload_flit(list(range(16)))]
            attached = attach(raw)
            exp30 = BM.UbDllBcrc().eat(attached[0], last=True)
            await self._beat(start=1, valid=1, last=1, data=attached[0])
            self.check(1, as_int(self.dut.done, "done"), "xia svl done")
            self.check(pack_word(exp30, 0, 0), as_int(self.dut.crc_word, "crc_word"),
                       "xia svl crc_word")
            sample_bcrc("xia_start_valid_last", 1, self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_xia_start_only(self) -> None:
        """Xia §2.6: start&&!valid loads INIT and ignores data_in."""
        name = "xia_start_only"
        try:
            from tb.vibe_uvm.golden import bcrc as BM

            attached = attach([payload_flit([0x11] * 16)])
            model = BM.UbDllBcrc()
            model.start()
            exp30 = model.eat(attached[0], last=True)
            await self._beat(start=1, valid=0, last=0, data=(1 << 160) - 1)
            await self._beat(start=0, valid=1, last=1, data=attached[0])
            self.check(1, as_int(self.dut.done, "done"), "xia start-only done")
            self.check(pack_word(exp30, 0, 0), as_int(self.dut.crc_word, "crc_word"),
                       "xia start-only crc_word")
            sample_bcrc("xia_start_only", 1, self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise

    async def case_xia_start_mid_restart(self) -> None:
        """Xia §2.6: start after a non-last block reseeds INIT."""
        name = "xia_start_mid_restart"
        try:
            from tb.vibe_uvm.golden import bcrc as BM

            partial = BM.bytes_to_flit(list(range(20)))
            restart = attach([payload_flit([0x22] * 16)])
            model = BM.UbDllBcrc()
            model.start()
            model.eat(partial, last=False)
            model.start()
            exp30 = model.eat(restart[0], last=True)
            await self._beat(start=1, valid=1, last=0, data=partial)
            await self._beat(start=1, valid=1, last=1, data=restart[0])
            self.check(1, as_int(self.dut.done, "done"), "xia mid-start done")
            self.check(pack_word(exp30, 0, 0), as_int(self.dut.crc_word, "crc_word"),
                       "xia mid-start crc_word")
            sample_bcrc("xia_start_mid_restart", 1, self.hooks)
            self.rec.pass_(name, TP)
        except Exception as exc:
            self.rec.fail(name, TP, str(exc))
            raise


uvm_component_utils(BcrcLeafTest)


@cocotb.test()
async def test_ub_bcrc(dut):
    await leaf_entry(dut, "BcrcLeafTest")
