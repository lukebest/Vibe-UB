"""Apply a plan to the fake handle + scoreboard (no RTL, no cocotb)."""

from __future__ import annotations

from tb.tp.handle import FakeBypassHandle
from tb.tp.scoreboard import TpBypassScoreboard
from tb.tp.sequences import Step, expected_compares


def run_plan(
    plan: list[Step],
    *,
    handle: FakeBypassHandle | None = None,
    scoreboard: TpBypassScoreboard | None = None,
) -> tuple[FakeBypassHandle, TpBypassScoreboard, int]:
    handle = handle if handle is not None else FakeBypassHandle()
    sb = scoreboard if scoreboard is not None else TpBypassScoreboard()
    for kind, payload in plan:
        if kind == "tx":
            sb.expect_tx(payload)
            actual = handle.send_tx(payload)
            if not sb.compare_tx(actual, f"tx tassn={payload.tassn}"):
                sb.assert_clean()
        elif kind == "rx":
            got = sb.expect_rx(payload)
            actual = handle.send_rx(payload)
            if got is None:
                if actual is not None:
                    raise AssertionError("drop must not deliver")
                continue
            if actual is None:
                raise AssertionError("keep RX produced no delivery")
            if not sb.compare_rx(actual, "rx"):
                sb.assert_clean()
        elif kind == "flush":
            sb.apply_flush()
            handle.flush = True
        elif kind == "end_flush":
            sb.end_flush()
            handle.flush = False
        elif kind == "link_down":
            sb.apply_link_down()
            handle.link_up = False
            handle.flush = True
        elif kind == "link_up":
            sb.ref.nw_link_up = True
            sb.end_flush()
            handle.link_up = True
            handle.flush = False
        else:
            raise ValueError(f"unknown step {kind!r}")
    want = expected_compares(plan)
    sb.assert_done(want)
    return handle, sb, want


__all__ = ["run_plan"]
