"""cocotb entry for ``ub_cmn_mem_1r1w``. Loaded only by the Verilator runner."""

from __future__ import annotations

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge

from tb.cmn.coverage import Mem1r1wCoverage
from tb.cmn.driver import Mem1r1wDriver
from tb.cmn.scoreboard import Mem1r1wScoreboard
from tb.cmn.sequences import expected_violation, make_sequence


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw, 0) if raw else default


def _sample_int(sig):
    val = sig.value
    is_res = getattr(val, "is_resolvable", None)
    if is_res is False:
        return None
    try:
        return int(val)
    except ValueError:
        return None


def _require_ports(dut) -> None:
    needed = ("clk", "we", "waddr", "wdata", "re", "raddr", "rdata")
    missing = [n for n in needed if not hasattr(dut, n)]
    if missing:
        raise AssertionError(
            "DUT/wrapper missing contract ports "
            f"{missing}; have={[p for p in dir(dut) if not p.startswith('_')]}"
        )


@cocotb.test()
async def test_ub_cmn_mem_1r1w(dut):
    _require_ports(dut)
    seed = _env_int("CMN_SEED", 1)
    case = os.environ.get("CMN_CASE", "random")
    depth = _env_int("CMN_DEPTH", 8)
    width = _env_int("CMN_WIDTH", 16)
    anur = bool(_env_int("CMN_ASSERT_NO_UNINIT_READ", 1))
    print(f"SEED {seed}", flush=True)
    print(
        f"CMN case={case} DEPTH={depth} WIDTH={width} "
        f"ASSERT_NO_UNINIT_READ={int(anur)} "
        f"variant={os.environ.get('CMN_VARIANT', '?')} "
        f"netlist={os.environ.get('CMN_NETLIST', '?')}",
        flush=True,
    )

    driver = Mem1r1wDriver()
    scoreboard = Mem1r1wScoreboard(depth, width, assert_no_uninit_read=anur)
    coverage = Mem1r1wCoverage()
    driver.idle(dut)

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    for _ in range(2):
        await RisingEdge(dut.clk)

    cycles = make_sequence(case, depth, width, seed, assert_no_uninit_read=anur)
    want = expected_violation(case, anur)
    saw = False
    last = len(cycles) - 1

    for i, cycle in enumerate(cycles):
        driver.drive(dut, cycle)
        _expected, flags = scoreboard.predict(*cycle.as_tuple())
        await RisingEdge(dut.clk)
        await ReadOnly()
        actual = _sample_int(dut.rdata)
        coverage.sample(
            depth=depth,
            width=width,
            assert_no_uninit_read=anur,
            we=cycle.we,
            waddr=cycle.waddr,
            re=cycle.re,
            raddr=cycle.raddr,
        )
        violating = bool(want) and i == last
        if violating:
            if not scoreboard.last_saw(want):
                raise AssertionError(
                    f"expected {want} on cycle {i}, flags={flags}"
                )
            saw = True
        elif flags:
            raise AssertionError(f"unexpected checker flags on cycle {i}: {flags}")
        elif not scoreboard.compare_rdata(actual, f"rdata@{i}"):
            raise AssertionError(
                "model bitwise rdata mismatch: " + "; ".join(scoreboard.mismatches)
            )

    if want and not saw:
        raise AssertionError(f"checker did not report {want}: {scoreboard.all_flags}")
    if not want:
        scoreboard.assert_clean()
    print(f"PASS ub_cmn_mem_1r1w case={case} cover={sorted(coverage.hits)}", flush=True)
