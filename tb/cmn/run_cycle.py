"""Shared cycle stepper for the fake handle and scoreboard."""

from __future__ import annotations

from tb.cmn.coverage import Mem1r1wCoverage
from tb.cmn.driver import Mem1r1wDriver
from tb.cmn.handle import FakeMemHandle
from tb.cmn.items import MemCycle
from tb.cmn.scoreboard import Mem1r1wScoreboard


def step_fake(
    handle: FakeMemHandle,
    scoreboard: Mem1r1wScoreboard,
    driver: Mem1r1wDriver,
    coverage: Mem1r1wCoverage,
    cycle: MemCycle,
    *,
    expect_violation: str | None = None,
    compare: bool = True,
) -> tuple[int | None, list[str]]:
    """Drive, tick fake DUT + scoreboard, compare, and sample coverage."""
    driver.drive(handle, cycle)
    driven = handle.sample_inputs()
    if driven != cycle.as_tuple():
        raise AssertionError(f"driver did not present cycle {cycle}: got {driven}")
    expected, flags = scoreboard.predict(*cycle.as_tuple())
    actual = handle.posedge()
    coverage.sample(
        depth=scoreboard.depth,
        width=scoreboard.width,
        assert_no_uninit_read=scoreboard.assert_no_uninit_read,
        we=cycle.we,
        waddr=cycle.waddr,
        re=cycle.re,
        raddr=cycle.raddr,
    )
    if expect_violation:
        if not scoreboard.last_saw(expect_violation):
            raise AssertionError(
                f"expected {expect_violation} on this cycle, flags={flags}"
            )
    elif flags:
        raise AssertionError(f"unexpected checker flags: {flags}")
    if compare:
        if not scoreboard.compare_rdata(actual, "rdata"):
            raise AssertionError(
                "model bitwise rdata mismatch: " + "; ".join(scoreboard.mismatches)
            )
    return expected, flags


def run_cycles(
    depth: int,
    width: int,
    cycles: list[MemCycle],
    *,
    assert_no_uninit_read: bool = True,
    expect_violation: str | None = None,
    coverage: Mem1r1wCoverage | None = None,
    compare: bool = True,
) -> tuple[FakeMemHandle, Mem1r1wScoreboard, Mem1r1wCoverage]:
    handle = FakeMemHandle(
        depth, width, assert_no_uninit_read=assert_no_uninit_read
    )
    scoreboard = Mem1r1wScoreboard(
        depth, width, assert_no_uninit_read=assert_no_uninit_read
    )
    driver = Mem1r1wDriver()
    cov = coverage if coverage is not None else Mem1r1wCoverage()
    # No DUT reset port. Array starts undefined (model reset_written).
    handle.undefine_array()
    scoreboard.ref.reset_written()
    saw = False
    last = len(cycles) - 1
    for i, cycle in enumerate(cycles):
        violating = bool(expect_violation) and i == last
        step_fake(
            handle,
            scoreboard,
            driver,
            cov,
            cycle,
            expect_violation=expect_violation if violating else None,
            compare=compare and not violating,
        )
        if expect_violation and scoreboard.last_saw(expect_violation):
            saw = True
    if expect_violation and not saw:
        raise AssertionError(
            f"checker did not report {expect_violation}: {scoreboard.all_flags}"
        )
    if not expect_violation:
        scoreboard.assert_clean()
    return handle, scoreboard, cov
