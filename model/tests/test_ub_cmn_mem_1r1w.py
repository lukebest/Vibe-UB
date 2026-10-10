"""ub_cmn_mem_1r1w golden. CODING_STYLE §10 / PR #20 (Xia timing proposal)."""

from __future__ import annotations

import random

import pytest

from model.ub_cmn_mem_1r1w import (
    UbCmnMem1r1w,
    UbCmnMem1r1wSimpleRef,
    UbCmnMemAddrError,
    UbCmnMemUnwrittenError,
    clog2,
)


def test_clog2_matches_verilog():
    assert clog2(1) == 0
    assert clog2(2) == 1
    assert clog2(3) == 2
    assert clog2(4) == 2
    assert clog2(5) == 3
    assert clog2(8) == 3


def test_aw_is_clog2_depth():
    m = UbCmnMem1r1w(depth=5, width=16)
    assert m.aw == 3
    assert m.depth == 5
    assert m.width == 16


def test_rdata_undefined_before_first_read():
    m = UbCmnMem1r1w(8, 16)
    assert m.rdata is None
    assert m.rdata_valid is False
    assert m.is_defined is False
    assert m.tick(1, 3, 0xA5A5, 0, 0) is None
    assert m.is_defined is False


def test_write_then_read_one_cycle_latency():
    m = UbCmnMem1r1w(8, 16)
    m.tick(1, 3, 0xA5A5, 0, 0)
    assert m.tick(0, 0, 0, 1, 3) == 0xA5A5
    assert m.rdata == 0xA5A5
    assert m.rdata_valid is True
    assert m.is_defined is True


def test_rdata_holds_when_re_low():
    m = UbCmnMem1r1w(4, 8)
    m.tick(1, 1, 0x3C, 0, 0)
    m.tick(0, 0, 0, 1, 1)
    assert m.rdata == 0x3C
    m.tick(0, 0, 0, 0, 0)
    m.tick(1, 2, 0x11, 0, 0)
    assert m.rdata == 0x3C
    assert m.is_defined is True


def test_same_address_read_old():
    m = UbCmnMem1r1w(4, 8)
    m.tick(1, 2, 0x10, 0, 0)
    assert m.tick(1, 2, 0x20, 1, 2) == 0x10
    assert m.tick(0, 0, 0, 1, 2) == 0x20


def test_wdata_masked_to_width():
    m = UbCmnMem1r1w(2, 4)
    m.tick(1, 0, 0x1F, 0, 0)
    assert m.tick(0, 0, 0, 1, 0) == 0xF


def test_out_of_range_waddr_raises():
    m = UbCmnMem1r1w(5, 8)
    with pytest.raises(UbCmnMemAddrError, match="waddr=7"):
        m.tick(1, 7, 1, 0, 0)
    assert m.flags
    assert m.is_defined is False


def test_out_of_range_raddr_raises():
    m = UbCmnMem1r1w(5, 8)
    m.tick(1, 0, 1, 0, 0)
    with pytest.raises(UbCmnMemAddrError, match="raddr=5"):
        m.tick(0, 0, 0, 1, 5)
    assert m.is_defined is False


def test_read_unwritten_raises():
    m = UbCmnMem1r1w(4, 8)
    with pytest.raises(UbCmnMemUnwrittenError, match="never-written"):
        m.tick(0, 0, 0, 1, 0)
    assert m.rdata is None
    assert m.is_defined is False


def test_same_cycle_write_read_unwritten_still_flags():
    # read-old of a never-written entry is still unwritten
    m = UbCmnMem1r1w(4, 8)
    with pytest.raises(UbCmnMemUnwrittenError):
        m.tick(1, 1, 0xAA, 1, 1)
    assert m._mem[1] == 0xAA
    assert m.written[1]
    assert m.rdata is None
    assert m.is_defined is False


def test_reset_makes_array_undefined_rdata_register_holds():
    m = UbCmnMem1r1w(4, 8)
    m.tick(1, 0, 0x55, 0, 0)
    m.tick(0, 0, 0, 1, 0)
    assert m.rdata == 0x55
    m.reset_written()
    assert m._mem[0] is None
    assert m.rdata == 0x55
    assert m.is_defined is True
    assert not any(m.written)
    with pytest.raises(UbCmnMemUnwrittenError):
        m.tick(0, 0, 0, 1, 0)
    assert m.rdata is None
    assert m.is_defined is False


def test_nonstrict_flags_without_raise():
    m = UbCmnMem1r1w(4, 8, strict=False)
    m.tick(1, 9, 1, 1, 2)
    assert len(m.flags) == 2
    assert "UbCmnMemAddrError" in m.flags[0]
    assert "UbCmnMemUnwrittenError" in m.flags[1]
    assert m.rdata is None
    assert m.is_defined is False


def test_assert_no_uninit_read_off_returns_undefined():
    # valid_outside: owner masks with an external valid bit.
    m = UbCmnMem1r1w(4, 8, assert_no_uninit_read=False)
    assert m.assert_no_uninit_read is False
    assert m.tick(0, 0, 0, 1, 0) is None
    assert m.rdata is None
    assert m.rdata_valid is False
    assert m.is_defined is False
    assert not m.flags
    m.tick(1, 0, 0x22, 0, 0)
    assert m.tick(0, 0, 0, 1, 0) == 0x22
    assert m.is_defined is True


def test_assert_no_uninit_read_off_still_flags_oor():
    m = UbCmnMem1r1w(5, 8, assert_no_uninit_read=False)
    with pytest.raises(UbCmnMemAddrError):
        m.tick(1, 7, 1, 0, 0)


@pytest.mark.parametrize("depth,width,seed,n", [(8, 16, 1, 200), (5, 9, 2, 150)])
def test_random_legal_vs_simple_ref(depth, width, seed, n):
    rng = random.Random(seed)
    dut = UbCmnMem1r1w(depth, width)
    ref = UbCmnMem1r1wSimpleRef(depth, width)
    written = [False] * depth
    for _ in range(n):
        we = bool(rng.randrange(2))
        re = bool(rng.randrange(2))
        waddr = rng.randrange(depth)
        raddr = rng.randrange(depth)
        wdata = rng.randrange(1 << width)
        if re and not written[raddr]:
            re = False
        got = dut.tick(we, waddr, wdata, re, raddr)
        exp = ref.tick(we, waddr, wdata, re, raddr)
        if dut.is_defined:
            assert got == exp
            assert dut.rdata_valid is True
        else:
            assert got is None
            assert exp is None
        if we:
            written[waddr] = True
