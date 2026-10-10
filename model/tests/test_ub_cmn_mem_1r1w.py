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
    variant_name,
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


def test_wmask_w_defaults_to_width_no_extra_port():
    m = UbCmnMem1r1w(8, 16)
    assert m.wmask_w == 16
    assert m.nseg == 1
    assert m.name == "ub_cmn_mem_1r1w_d8w16"
    # NSEG=1: rdata_valid stays a bool (TB scoreboard uses `is True`).
    m.tick(1, 0, 0x1234, 0, 0)
    assert m.tick(0, 0, 0, 1, 0) == 0x1234
    assert m.rdata_valid is True
    assert m.is_defined is True
    assert m.valid_mask == 1


def test_width_must_be_multiple_of_wmask_w():
    with pytest.raises(ValueError, match="multiple"):
        UbCmnMem1r1w(8, 16, wmask_w=12)


def test_variant_name_appends_m_only_when_nseg_gt_1():
    assert variant_name(512, 512) == "ub_cmn_mem_1r1w_d512w512"
    assert variant_name(512, 512, 512) == "ub_cmn_mem_1r1w_d512w512"
    assert variant_name(512, 512, 64) == "ub_cmn_mem_1r1w_d512w512m64"
    assert variant_name(64, 64, 16) == "ub_cmn_mem_1r1w_d64w64m16"
    m = UbCmnMem1r1w(64, 64, wmask_w=16)
    assert m.nseg == 4
    assert m.name == "ub_cmn_mem_1r1w_d64w64m16"


def test_single_segment_write():
    m = UbCmnMem1r1w(4, 16, wmask_w=4, assert_no_uninit_read=False)
    # Write only segment 1 (bits [7:4]).
    m.tick(1, 0, 0xABCD, 0, 0, wmask=0b0010)
    assert m.written[0] == 0b0010
    m.tick(0, 0, 0, 1, 0)
    assert m.rdata_valid == 0b0010
    assert m.is_defined is False
    assert m.segment_defined(1)
    assert not m.segment_defined(0)
    assert m.segment_bits(m.rdata, 1) == 0xC
    assert m.compare_valid_segments(0x00C0)
    assert m.compare_valid_segments(0xFFCF) is False


def test_adjacent_segment_write():
    m = UbCmnMem1r1w(4, 16, wmask_w=4, assert_no_uninit_read=False)
    # Segments 1 and 2 (bits [11:4]).
    m.tick(1, 1, 0xABCD, 0, 0, wmask=0b0110)
    m.tick(0, 0, 0, 1, 1)
    assert m.rdata_valid == 0b0110
    assert m.segment_bits(m.rdata, 1) == 0xC
    assert m.segment_bits(m.rdata, 2) == 0xB
    assert not m.segment_defined(0)
    assert not m.segment_defined(3)


def test_all_segment_write():
    m = UbCmnMem1r1w(4, 16, wmask_w=4)
    m.tick(1, 2, 0xABCD, 0, 0, wmask=0b1111)
    assert m.written[2] == 0b1111
    assert m.tick(0, 0, 0, 1, 2) == 0xABCD
    assert m.rdata_valid == 0b1111
    assert m.is_defined is True
    # Default wmask (None) is also all-segments.
    m.tick(1, 3, 0x1234, 0, 0)
    assert m.tick(0, 0, 0, 1, 3) == 0x1234


def test_same_cycle_read_old_per_segment():
    m = UbCmnMem1r1w(4, 16, wmask_w=4)
    m.tick(1, 0, 0x1111, 0, 0, wmask=0b1111)
    # Same-address write of segments 0+1; read must return OLD per segment.
    got = m.tick(1, 0, 0xEEEE, 1, 0, wmask=0b0011)
    assert got == 0x1111
    assert m.segment_bits(got, 0) == 0x1
    assert m.segment_bits(got, 1) == 0x1
    assert m.segment_bits(got, 2) == 0x1
    assert m.segment_bits(got, 3) == 0x1
    # Next read sees new segs 0+1, old segs 2+3.
    got = m.tick(0, 0, 0, 1, 0)
    assert m.segment_bits(got, 0) == 0xE
    assert m.segment_bits(got, 1) == 0xE
    assert m.segment_bits(got, 2) == 0x1
    assert m.segment_bits(got, 3) == 0x1
    assert got == 0x11EE


def test_uninit_per_segment_assert_on():
    m = UbCmnMem1r1w(4, 16, wmask_w=4, assert_no_uninit_read=True)
    # Only segment 0 written: any-segment-unwritten is a violation.
    m.tick(1, 0, 0x000F, 0, 0, wmask=0b0001)
    with pytest.raises(UbCmnMemUnwrittenError, match="never-written"):
        m.tick(0, 0, 0, 1, 0)
    assert m.segment_defined(0)
    assert not m.is_defined
    # Fill the remaining segments, then the read is legal.
    m.tick(1, 0, 0xFFF0, 0, 0, wmask=0b1110)
    assert m.written[0] == 0b1111
    assert m.tick(0, 0, 0, 1, 0) == 0xFFFF
    assert m.is_defined is True


def test_uninit_per_segment_assert_off():
    m = UbCmnMem1r1w(4, 16, wmask_w=4, assert_no_uninit_read=False)
    m.tick(1, 0, 0x00A0, 0, 0, wmask=0b0010)
    got = m.tick(0, 0, 0, 1, 0)
    assert not m.flags
    assert m.rdata_valid == 0b0010
    assert m.is_defined is False
    assert m.segment_bits(got, 1) == 0xA
    assert m.compare_valid_segments(0x00A0)
    # Completely unwritten address: no violation, rdata undefined.
    assert m.tick(0, 0, 0, 1, 1) is None
    assert m.rdata_valid == 0
    assert m.is_defined is False
    assert not m.flags


def test_unmasked_segments_hold_old_value():
    m = UbCmnMem1r1w(4, 16, wmask_w=4)
    m.tick(1, 0, 0xABCD, 0, 0, wmask=0b1111)
    # Overwrite only segment 0.
    m.tick(1, 0, 0x0001, 0, 0, wmask=0b0001)
    assert m.tick(0, 0, 0, 1, 0) == 0xABC1


@pytest.mark.parametrize("depth,width,wmask_w,seed,n", [(8, 16, 4, 3, 200)])
def test_random_segmented_vs_simple_ref(depth, width, wmask_w, seed, n):
    rng = random.Random(seed)
    nseg = width // wmask_w
    dut = UbCmnMem1r1w(depth, width, wmask_w=wmask_w)
    ref = UbCmnMem1r1wSimpleRef(depth, width, wmask_w=wmask_w)
    written = [0] * depth
    all_seg = (1 << nseg) - 1
    for _ in range(n):
        we = bool(rng.randrange(2))
        re = bool(rng.randrange(2))
        waddr = rng.randrange(depth)
        raddr = rng.randrange(depth)
        wdata = rng.randrange(1 << width)
        wmask = rng.randrange(1, 1 << nseg)
        if re and written[raddr] != all_seg:
            re = False
        got = dut.tick(we, waddr, wdata, re, raddr, wmask=wmask)
        exp = ref.tick(we, waddr, wdata, re, raddr, wmask=wmask)
        if dut.is_defined:
            assert got == exp
            assert dut.rdata_valid == all_seg
            assert dut.compare_valid_segments(exp)
        if we:
            written[waddr] |= wmask
