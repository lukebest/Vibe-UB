"""NW↔TP monitor/driver self-test on mock signals (LAYER_CONTRACTS §2)."""

from __future__ import annotations

from tb.contracts.model import CFG9, FLIT_W, bypass_cfg_ok
from tb.contracts.nw_tp import (
    ALL_SIGNALS,
    NwTpDriver,
    NwTpHook,
    NwTpMonitor,
    mock_bundle,
    rx_expected,
    tx_expected,
)
from tb.contracts.scoreboard import ContractScoreboard


def _env():
    sigs = mock_bundle()
    drv = NwTpDriver(sigs)
    mon = NwTpMonitor(sigs)
    drv.idle_tx()
    drv.idle_rx()
    drv.set_tx_ready(0)
    drv.set_rx_ready(0)
    drv.set_link_up(1)
    drv.set_flush(0)
    drv.clear_drop()
    return sigs, drv, mon


def test_signal_names_match_contract():
    sigs = mock_bundle()
    assert set(sigs) == set(ALL_SIGNALS)
    assert "tp2nw_bypass" in sigs
    assert "nw2tp_err" in sigs
    assert "nw_link_up" in sigs
    assert sigs["tp2nw_data"].width == FLIT_W


def test_tx_and_rx_each_compare_to_model():
    _sigs, drv, mon = _env()
    sb = ContractScoreboard("nw_tp", {"tx": 2, "rx": 2, "total": 4})
    hook = NwTpHook(sb, mon)

    drv.set_tx_ready(1)
    drv.present_tx(data=0x11, sop=1, eop=1, sl=0, nlp=0, bypass=1)
    hook.check_tx(tx_expected(data=0x11, sop=1, eop=1, sl=0, nlp=0, bypass=1), "tx0")
    drv.present_tx(data=0x22, sop=1, eop=0, sl=1, nlp=1, bypass=0)
    hook.check_tx(tx_expected(data=0x22, sop=1, eop=0, sl=1, nlp=1, bypass=0), "tx1")

    drv.set_rx_ready(1)
    drv.present_rx(data=0xAA, sop=1, eop=1, err=0)
    hook.check_rx(rx_expected(data=0xAA, sop=1, eop=1, err=0), "rx0")
    drv.present_rx(data=0xBB, sop=0, eop=1, err=1)
    hook.check_rx(rx_expected(data=0xBB, sop=0, eop=1, err=1), "rx1")

    sb.check()


def test_no_fire_when_ready_low():
    _sigs, drv, mon = _env()
    drv.set_tx_ready(0)
    drv.present_tx(data=1, sop=1, eop=1, bypass=1)
    assert mon.sample_tx() is None
    drv.set_tx_ready(1)
    assert mon.sample_tx() is not None


def test_bypass_cfg9_model_on_tx_side():
    assert bypass_cfg_ok(1, CFG9)
    _sigs, drv, mon = _env()
    sb = ContractScoreboard("bypass", {"tx": 1, "rx": 0, "total": 1})
    hook = NwTpHook(sb, mon)
    drv.set_tx_ready(1)
    drv.present_tx(data=0, sop=1, eop=1, sl=0, nlp=0, bypass=1)
    hook.check_tx(tx_expected(data=0, sop=1, eop=1, sl=0, nlp=0, bypass=1), "byp")
    sb.check()
    assert mon.sample_tx()["bypass"] == 1


def test_link_down_observed():
    _sigs, drv, mon = _env()
    drv.set_link_up(0)
    drv.set_flush(1)
    assert mon.link_up() == 0
    assert mon.flush() == 1


def test_sop_eop_single_flit():
    _sigs, drv, mon = _env()
    sb = ContractScoreboard("sop_eop", {"tx": 1, "rx": 1, "total": 2})
    hook = NwTpHook(sb, mon)
    drv.set_tx_ready(1)
    drv.set_rx_ready(1)
    drv.present_tx(data=7, sop=1, eop=1)
    hook.check_tx(tx_expected(data=7, sop=1, eop=1), "tx")
    drv.present_rx(data=7, sop=1, eop=1)
    hook.check_rx(rx_expected(data=7, sop=1, eop=1, err=0), "rx")
    sb.check()
