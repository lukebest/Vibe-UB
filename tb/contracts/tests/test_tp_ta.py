"""TP↔TA monitor/driver self-test on mock signals (LAYER_CONTRACTS §3)."""

from __future__ import annotations

from tb.contracts.model import INI_TASSN_W, done_fail_ok
from tb.contracts.scoreboard import ContractScoreboard
from tb.contracts.tp_ta import (
    ALL_SIGNALS,
    TpTaDriver,
    TpTaHook,
    TpTaMonitor,
    mock_bundle,
    payload_expected,
    submit_expected,
)


def _env():
    sigs = mock_bundle()
    drv = TpTaDriver(sigs)
    mon = TpTaMonitor(sigs)
    drv.idle_submit()
    drv.idle_complete()
    drv.set_op_ready(0)
    drv.set_data_ready(0)
    drv.set_deliver_op_ready(0)
    drv.set_deliver_data_ready(0)
    drv.set_link_up(1)
    drv.set_flush(0)
    return sigs, drv, mon


def test_signal_names_match_contract():
    sigs = mock_bundle()
    assert set(sigs) == set(ALL_SIGNALS)
    assert "ta2tp_op_valid" in sigs
    assert "ta2tp_tassn" in sigs
    assert sigs["ta2tp_tassn"].width == INI_TASSN_W
    assert "tp2ta_done" in sigs
    assert "tp2ta_fail" in sigs


def test_submit_and_complete_each_compare_to_model():
    _sigs, drv, mon = _env()
    sb = ContractScoreboard(
        "tp_ta",
        {"submit": 2, "complete": 2, "total": 4},
    )
    hook = TpTaHook(sb, mon)

    drv.set_op_ready(1)
    drv.present_op(opcode=0x10, tassn=0x0001, mode=0, bypass=1)
    hook.check_submit(submit_expected(opcode=0x10, tassn=0x0001, mode=0, bypass=1), "op0")
    drv.set_data_ready(1)
    drv.present_payload(data=0x55, sop=1, eop=1)
    hook.check_submit_data(payload_expected(data=0x55, sop=1, eop=1), "d0")

    drv.pulse_done(tassn=0x0001, fail=0)
    hook.check_complete(
        {"done": 1, "fail": 0, "tassn": 0x0001, "err": 0},
        "done0",
    )
    drv.set_deliver_op_ready(1)
    drv.present_deliver_op(opcode=0x11, tassn=0x0002, mode=0, bypass=1)
    hook.check_deliver(
        {"opcode": 0x11, "tassn": 0x0002, "mode": 0, "bypass": 1},
        "del0",
    )
    sb.check()


def test_done_fail_mutex_on_complete_side():
    _sigs, drv, mon = _env()
    drv.pulse_done(tassn=9, fail=0)
    got = mon.sample_complete()
    assert got is not None
    assert done_fail_ok(got["done"], got["fail"])
    drv.pulse_done(tassn=9, fail=1)
    got = mon.sample_complete()
    assert got is not None
    assert done_fail_ok(got["done"], got["fail"])
    assert got["fail"] == 1 and got["done"] == 0


def test_tassn_16bit_on_submit_side():
    _sigs, drv, mon = _env()
    sb = ContractScoreboard("tassn", {"submit": 1, "complete": 0, "total": 1})
    hook = TpTaHook(sb, mon)
    drv.set_op_ready(1)
    drv.present_op(opcode=1, tassn=0xABCD, bypass=1)
    hook.check_submit(submit_expected(opcode=1, tassn=0xABCD, mode=0, bypass=1))
    sb.check()


def test_bypass_complete_does_not_require_tpack_state():
    _sigs, drv, mon = _env()
    sb = ContractScoreboard("byp", {"submit": 1, "complete": 1, "total": 2})
    hook = TpTaHook(sb, mon)
    drv.set_op_ready(1)
    drv.present_op(opcode=2, tassn=3, bypass=1)
    hook.check_submit(submit_expected(opcode=2, tassn=3, mode=0, bypass=1), "sub")
    drv.pulse_done(tassn=3)
    hook.check_complete({"done": 1, "fail": 0, "tassn": 3, "err": 0}, "fin")
    sb.check()
    assert mon.sample_submit_op()["bypass"] == 1
