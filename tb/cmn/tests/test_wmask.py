"""Python self-check of segmented write (WMASK_W / NSEG>1). No RTL."""

from __future__ import annotations

import pytest

from tb.cmn.coverage import Mem1r1wCoverage
from tb.cmn.driver import Mem1r1wDriver
from tb.cmn.handle import FakeMemHandle, WmaskSwapFakeHandle
from tb.cmn.items import MemCycle
from tb.cmn.run_cycle import run_cycles, step_fake
from tb.cmn.scoreboard import Mem1r1wScoreboard
from tb.cmn.sequences import (
    WMASK_CASES,
    WMASK_COMBOS,
    expected_violation,
    make_sequence,
    seq_wmask_onehot,
    seq_wmask_single,
)

SEED = 1
DEPTH, WIDTH, WMASK_W = 4, 16, 4
NSEG = WIDTH // WMASK_W


@pytest.mark.parametrize("depth,width,wmask_w,anur", WMASK_COMBOS)
@pytest.mark.parametrize("case", WMASK_CASES)
def test_wmask_positive_cases_match_model(depth, width, wmask_w, anur, case):
    print(f"SEED {SEED}", flush=True)
    nseg = width // wmask_w
    cycles = make_sequence(
        case,
        depth,
        width,
        SEED,
        assert_no_uninit_read=anur,
        wmask_w=wmask_w,
    )
    handle, sb, _ = run_cycles(
        depth,
        width,
        cycles,
        wmask_w=wmask_w,
        assert_no_uninit_read=anur,
    )
    assert handle.trace == [c.as_driven(nseg) for c in cycles]
    assert sb.n_mismatch == 0
    assert sb.n_compare > 0
    assert sb.n_compare == sum(sb.n_compare_seg)
    if case == "wmask_single":
        sb.assert_seg_compares(compared=[0], min_each=1)
    else:
        sb.assert_seg_compares(min_each=1)


def test_wmask_single_written_seg_compared_others_hold():
    handle, sb, _ = run_cycles(
        DEPTH, WIDTH, seq_wmask_single(DEPTH, WIDTH, WMASK_W), wmask_w=WMASK_W
    )
    # After fill 0x1111 then write seg0 with unique low nibble, others stay 0x1.
    assert sb.ref.rdata is not None
    assert sb.ref.segment_bits(sb.ref.rdata, 0) == ((0x5A) & 0xF)
    for seg in range(1, NSEG):
        assert sb.ref.segment_bits(sb.ref.rdata, seg) == 0x1
    assert handle.inner._mem[0] == sb.ref.rdata
    sb.assert_seg_compares(compared=[0], min_each=1)
    assert sb.n_compare_seg[0] >= 2  # fill-read + after single-seg write


def test_wmask_adjacent_updates_only_those_segs():
    handle, sb, _ = run_cycles(
        DEPTH,
        WIDTH,
        make_sequence("wmask_adjacent", DEPTH, WIDTH, SEED, wmask_w=WMASK_W),
        wmask_w=WMASK_W,
    )
    got = sb.ref.rdata
    assert got is not None
    assert sb.ref.segment_bits(got, 0) == ((0x5A) & 0xF)
    assert sb.ref.segment_bits(got, 1) == ((0x5A + 0x11) & 0xF)
    assert sb.ref.segment_bits(got, 2) == 0x2
    assert sb.ref.segment_bits(got, 3) == 0x2
    sb.assert_seg_compares(compared=[0, 1], min_each=1)


def test_wmask_all_defines_every_segment():
    _h, sb, cov = run_cycles(
        DEPTH,
        WIDTH,
        make_sequence("wmask_all", DEPTH, WIDTH, SEED, wmask_w=WMASK_W),
        wmask_w=WMASK_W,
    )
    assert sb.is_defined is True
    assert sb.rdata_valid == 0b1111
    sb.assert_seg_compares(expected=[1, 1, 1, 1])
    cov.require("wmask_all")


def test_wmask_zero_does_not_change_word():
    _h, sb, cov = run_cycles(
        DEPTH,
        WIDTH,
        make_sequence("wmask_zero", DEPTH, WIDTH, SEED, wmask_w=WMASK_W),
        wmask_w=WMASK_W,
    )
    assert sb.ref.rdata == 0x3333
    # Defined rdata holds across the wmask=0 write, so that beat is compared too.
    sb.assert_seg_compares(expected=[3, 3, 3, 3])
    cov.require("wmask_zero")


def test_wmask_same_cycle_read_old_per_segment():
    _h, sb, _ = run_cycles(
        DEPTH,
        WIDTH,
        make_sequence("wmask_conflict", DEPTH, WIDTH, SEED, wmask_w=WMASK_W),
        wmask_w=WMASK_W,
    )
    # Last read sees new segs 0+1, old segs 2+3 (old fill was 0x1111).
    got = sb.ref.rdata
    assert got is not None
    assert sb.ref.segment_bits(got, 0) == ((0x5A) & 0xF)
    assert sb.ref.segment_bits(got, 1) == ((0x5A + 0x11) & 0xF)
    assert sb.ref.segment_bits(got, 2) == 0x1
    assert sb.ref.segment_bits(got, 3) == 0x1


def test_wmask_onehot_scan_catches_order():
    cycles = seq_wmask_onehot(DEPTH, WIDTH, WMASK_W)
    _h, sb, cov = run_cycles(DEPTH, WIDTH, cycles, wmask_w=WMASK_W)
    got = sb.ref.rdata
    assert got is not None
    for seg in range(NSEG):
        assert sb.ref.segment_bits(got, seg) == ((0x5A + seg * 0x11) & 0xF)
        assert sb.n_compare_seg[seg] > 0
    cov.require("wmask_onehot")
    sb.assert_seg_compares(min_each=1)


def test_wmask_partial_anur1_is_violation():
    cycles = make_sequence(
        "wmask_partial_uninit", DEPTH, WIDTH, SEED, wmask_w=WMASK_W
    )
    want = expected_violation("wmask_partial_uninit", True)
    assert want == "uninit"
    _h, sb, _ = run_cycles(
        DEPTH,
        WIDTH,
        cycles,
        wmask_w=WMASK_W,
        assert_no_uninit_read=True,
        expect_violation=want,
    )
    assert sb.saw("uninit")


def test_wmask_partial_anur0_compares_only_written_seg():
    cycles = make_sequence(
        "wmask_partial_ok",
        DEPTH,
        WIDTH,
        SEED,
        assert_no_uninit_read=False,
        wmask_w=WMASK_W,
    )
    _h, sb, _ = run_cycles(
        DEPTH, WIDTH, cycles, wmask_w=WMASK_W, assert_no_uninit_read=False
    )
    assert not sb.saw("uninit")
    assert sb.rdata_valid == 0b0001
    assert sb.is_defined is False
    sb.assert_seg_compares(compared=[0], untouched=[1, 2, 3], expected=[1, 0, 0, 0])
    assert sb.n_compare == 1


def test_scoreboard_catches_reversed_wmask():
    """Direction lock: a DUT that reverses wmask bit order must fail."""
    handle = WmaskSwapFakeHandle(DEPTH, WIDTH, wmask_w=WMASK_W)
    sb = Mem1r1wScoreboard(DEPTH, WIDTH, wmask_w=WMASK_W)
    driver = Mem1r1wDriver()
    cov = Mem1r1wCoverage()
    cycles = seq_wmask_onehot(DEPTH, WIDTH, WMASK_W)
    with pytest.raises(AssertionError):
        for cyc in cycles:
            step_fake(handle, sb, driver, cov, cyc)
        sb.assert_clean()
    assert sb.n_mismatch >= 1


def test_nseg1_rdata_valid_stays_bool():
    handle, sb, _ = run_cycles(
        4, 8, [MemCycle(we=1, waddr=0, wdata=0x5A), MemCycle(re=1, raddr=0)]
    )
    assert sb.nseg == 1
    assert sb.rdata_valid is True
    assert not hasattr(handle, "wmask")
    assert sb.n_compare == 1
    assert sb.n_compare_seg == [1]


def test_wmask_random_legal_tracks_written_mask():
    cycles = make_sequence(
        "random",
        DEPTH,
        WIDTH,
        SEED,
        assert_no_uninit_read=True,
        wmask_w=WMASK_W,
        random_n=40,
    )
    handle, sb, _ = run_cycles(
        DEPTH, WIDTH, cycles, wmask_w=WMASK_W, assert_no_uninit_read=True
    )
    assert sb.n_mismatch == 0
    if any(c.re for c in cycles):
        assert sb.n_compare > 0
        sb.assert_seg_compares()
    assert handle.nseg == NSEG
    assert hasattr(handle, "wmask")
