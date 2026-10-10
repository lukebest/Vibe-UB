"""Pure-Python self-check of the 1R1W driver / scoreboard (no RTL).

The architecture model is the oracle. A local write/read dict is not a pass.
"""

from __future__ import annotations

import pytest

from tb.cmn.coverage import Mem1r1wCoverage
from tb.cmn.driver import Mem1r1wDriver
from tb.cmn.handle import AddrAliasFakeHandle, BitSwapFakeHandle, FakeMemHandle
from tb.cmn.items import MemCycle
from tb.cmn.run_cycle import run_cycles, step_fake
from tb.cmn.scoreboard import Mem1r1wScoreboard
from tb.cmn.sequences import (
    NEGATIVE_CASES,
    POSITIVE_CASES,
    POSITIVE_COMBOS,
    expected_violation,
    make_sequence,
    seq_addr_onehot,
    seq_data_eq_addr,
    seq_data_onehot,
    seq_fill_fwd_rev,
)

SEED = 1


@pytest.mark.parametrize("depth,width,anur", POSITIVE_COMBOS)
@pytest.mark.parametrize("case", POSITIVE_CASES)
def test_positive_cases_match_model(depth, width, anur, case):
    print(f"SEED {SEED}", flush=True)
    cycles = make_sequence(case, depth, width, SEED, assert_no_uninit_read=anur)
    handle, sb, _cov = run_cycles(
        depth, width, cycles, assert_no_uninit_read=anur
    )
    assert handle.trace == [c.as_tuple() for c in cycles]
    assert sb.n_mismatch == 0
    assert sb.n_compare >= 1 or not any(c.re for c in cycles)


def test_conflict_read_old_is_model_old_not_new_write():
    """Same-address same-cycle must be read-old. A write==read check would pass wrongly."""
    handle, sb, _ = run_cycles(4, 8, make_sequence("conflict", 4, 8, SEED))
    # After write 0x10, conflict write 0x20 + read → model old 0x10, then 0x20.
    assert handle.inner.rdata == 0x20
    assert sb.ref.rdata == 0x20
    # Replay just the conflict cycle against a fresh model to pin the old value.
    from model.ub_cmn_mem_1r1w import UbCmnMem1r1w

    m = UbCmnMem1r1w(4, 8)
    m.tick(1, 2, 0x10, 0, 0)
    assert m.tick(1, 2, 0x20, 1, 2) == 0x10


def test_data_onehot_each_bit_against_model():
    handle, sb, cov = run_cycles(4, 8, seq_data_onehot(4, 8))
    assert sb.n_mismatch == 0
    assert sb.n_compare >= 8
    cov.require("params:4x8:anur=1")


def test_addr_onehot_unique_slots_against_model():
    """Address-bit swap would make the model disagree on rdata bits."""
    handle, sb, _ = run_cycles(5, 8, seq_addr_onehot(5, 8))
    assert sb.n_mismatch == 0
    # DEPTH=5 uses encodings 0,1,2,4 (3 is also written).
    written = [i for i, w in enumerate(handle.inner.written) if w]
    assert 0 in written and 1 in written and 2 in written and 4 in written


def test_fill_forward_and_reverse_readback():
    handle, sb, _ = run_cycles(5, 8, seq_fill_fwd_rev(5, 8))
    assert sb.n_mismatch == 0
    assert all(handle.inner.written)


def test_data_equals_address_pattern():
    handle, sb, _ = run_cycles(5, 9, seq_data_eq_addr(5, 9))
    assert sb.n_mismatch == 0
    for addr in range(5):
        assert handle.inner._mem[addr] == addr


def test_scoreboard_catches_rdata_bit_swap():
    """Direction lock: a DUT that swaps bits must fail vs the model."""
    depth, width = 4, 8
    handle = BitSwapFakeHandle(depth, width)
    sb = Mem1r1wScoreboard(depth, width)
    driver = Mem1r1wDriver()
    cov = Mem1r1wCoverage()
    cycles = [
        MemCycle(we=1, waddr=0, wdata=0x01),
        MemCycle(re=1, raddr=0),
    ]
    with pytest.raises(AssertionError, match="bit"):
        for cyc in cycles:
            step_fake(handle, sb, driver, cov, cyc)
        sb.assert_clean()
    assert sb.n_mismatch >= 1


def test_scoreboard_catches_address_bit_alias():
    """Direction lock: dropped address LSB must fail vs the model."""
    depth, width = 5, 8
    handle = AddrAliasFakeHandle(depth, width)
    sb = Mem1r1wScoreboard(depth, width)
    driver = Mem1r1wDriver()
    cov = Mem1r1wCoverage()
    cycles = [
        MemCycle(we=1, waddr=0, wdata=0x11),
        MemCycle(we=1, waddr=1, wdata=0x22),
        MemCycle(re=1, raddr=0),
        MemCycle(re=1, raddr=1),
    ]
    with pytest.raises(AssertionError):
        for cyc in cycles:
            step_fake(handle, sb, driver, cov, cyc)
        sb.assert_clean()
    assert sb.n_mismatch >= 1


def test_write_equals_read_is_not_a_pass():
    """A TB that only checks 'wrote X, read X' would pass this corrupted DUT."""
    depth, width = 4, 8
    handle = FakeMemHandle(depth, width)
    sb = Mem1r1wScoreboard(depth, width)
    driver = Mem1r1wDriver()
    driver.drive(handle, MemCycle(we=1, waddr=1, wdata=0xA5))
    sb.predict(1, 1, 0xA5, 0, 0)
    handle.posedge()
    driver.drive(handle, MemCycle(re=1, raddr=1))
    expected, _ = sb.predict(0, 0, 0, 1, 1)
    actual = handle.posedge()
    assert actual == expected == 0xA5
    # Inject a 'write==read' style false pass: claim 0xA5 while the model
    # expects hold of 0xA5 — then lie on a later cycle where model holds
    # but we present the last write to a *different* address.
    driver.drive(handle, MemCycle(we=1, waddr=2, wdata=0x3C, re=0, raddr=0))
    sb.predict(1, 2, 0x3C, 0, 0)
    handle.posedge()
    # Naive checker would accept 0x3C (last write). Model still holds 0xA5.
    assert sb.ref.rdata == 0xA5
    assert sb.compare(0x3C, sb.ref.rdata, "naive-last-write") is False
    with pytest.raises(AssertionError, match="mismatch"):
        sb.assert_clean()


@pytest.mark.parametrize("case", NEGATIVE_CASES)
def test_negative_checker_flags(case):
    cycles = make_sequence(case, 5, 8, SEED, assert_no_uninit_read=True)
    want = expected_violation(case, True)
    assert want is not None
    _h, sb, cov = run_cycles(
        5, 8, cycles, assert_no_uninit_read=True, expect_violation=want
    )
    assert sb.saw(want)
    if case.startswith("oor"):
        if case == "oor_waddr":
            cov.require("oor_waddr")
        else:
            cov.require("oor_raddr")


def test_non_pow2_oor_encodings_flag():
    """DEPTH=5, AW=3: encodings 5,6,7 are OOR (RTL does not truncate)."""
    for addr in (5, 6, 7):
        _h, sb, _ = run_cycles(
            5,
            8,
            [MemCycle(we=1, waddr=addr, wdata=1)],
            expect_violation="oor",
        )
        assert sb.saw("oor")


def test_uninit_off_does_not_flag():
    _h, sb, _ = run_cycles(
        4,
        8,
        make_sequence("uninit_ok", 4, 8, SEED, assert_no_uninit_read=False),
        assert_no_uninit_read=False,
    )
    assert not sb.saw("uninit")
    sb.assert_clean()


def test_uninit_off_still_flags_oor():
    _h, sb, _ = run_cycles(
        5,
        8,
        [MemCycle(we=1, waddr=7, wdata=1)],
        assert_no_uninit_read=False,
        expect_violation="oor",
    )
    assert sb.saw("oor")


def test_functional_cover_points():
    cov = Mem1r1wCoverage()
    for depth, width, anur in POSITIVE_COMBOS:
        for case in POSITIVE_CASES:
            cycles = make_sequence(
                case, depth, width, SEED, assert_no_uninit_read=anur
            )
            run_cycles(
                depth,
                width,
                cycles,
                assert_no_uninit_read=anur,
                coverage=cov,
            )
        run_cycles(
            depth,
            width,
            make_sequence("oor_waddr", depth, width, SEED),
            assert_no_uninit_read=anur,
            expect_violation="oor",
            coverage=cov,
        )
    cov.require("conflict", "boundary_0", "boundary_last", "oor_waddr")
    for depth, width, anur in POSITIVE_COMBOS:
        cov.require_param(depth, width, anur)


def test_driver_records_exact_ports():
    handle, _sb, _ = run_cycles(
        8,
        16,
        [
            MemCycle(we=1, waddr=3, wdata=0xA5A5),
            MemCycle(re=1, raddr=3),
        ],
    )
    assert handle.trace == [(1, 3, 0xA5A5, 0, 0), (0, 0, 0, 1, 3)]
