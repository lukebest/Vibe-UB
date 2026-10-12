"""ub_tp_bypass golden. LAYER_CONTRACTS §2 / §3; UB §6.3 / §6.3.2 / B.2.6."""

from __future__ import annotations

import inspect

import pytest

from model.tp.ub_tp_bypass import (
    CCI_W,
    CFG_BYPASS,
    DCNA_W,
    FLIT_W,
    FLITS_PER_BEAT,
    LBF_W,
    NLP_W,
    OPCODE_W,
    RT_W,
    SL_W,
    TASSN_W,
    TPMSN_W,
    UNKNOWNS,
    Flit,
    NwTxSideband,
    TaComplete,
    TaOp,
    UbTpBypass,
    UbTpBypassError,
    check_payload,
    iter_tx_beats,
)


def _flits(*data: int, single: bool | None = None) -> tuple[Flit, ...]:
    if single or len(data) == 1:
        return (Flit(data[0], sop=True, eop=True),)
    out = [Flit(data[0], sop=True, eop=False)]
    for word in data[1:-1]:
        out.append(Flit(word, sop=False, eop=False))
    out.append(Flit(data[-1], sop=False, eop=True))
    return tuple(out)


def _op(
    tassn: int = 1,
    *,
    opcode: int = 0x10,
    dcna: int = 0x00AB,
    bypass: bool = True,
) -> TaOp:
    return TaOp(opcode=opcode, tassn=tassn, bypass=bypass, dcna=dcna)


def _sb(
    *,
    sl: int = 2,
    nlp: int = 5,
    lbf: int = 0x3C,
    rt: int = 1,
    cci: int = 0x1122,
) -> NwTxSideband:
    return NwTxSideband(sl=sl, nlp=nlp, lbf=lbf, rt=rt, cci=cci)


def test_locked_widths_match_contract():
    assert FLIT_W == 160
    assert FLITS_PER_BEAT == 1
    assert (SL_W, NLP_W, DCNA_W, LBF_W, RT_W, CCI_W) == (4, 3, 16, 8, 2, 16)
    assert (OPCODE_W, TASSN_W, TPMSN_W) == (8, 16, 24)
    assert CFG_BYPASS == 9


def test_unknowns_listed_and_absent_from_api():
    blob = " ".join(UNKNOWNS).lower()
    assert "ta2tp_op_len" in blob
    assert "ta2tp_mode" in blob
    assert "rspst" in blob and "rspinfo" in blob
    assert "24-bit dcna" in blob
    assert "tah" in blob
    names = set(inspect.signature(TaOp).parameters)
    names |= set(inspect.signature(NwTxSideband).parameters)
    names |= set(inspect.signature(UbTpBypass.submit).parameters)
    names |= set(inspect.signature(UbTpBypass.receive).parameters)
    names |= set(inspect.signature(UbTpBypass.complete).parameters)
    assert "mode" not in names
    assert "op_len" not in names
    assert "rspst" not in names
    assert "rspinfo" not in names
    assert "dcna24" not in names
    src = inspect.getsource(UbTpBypass)
    assert "Unknowns" in inspect.getdoc(inspect.getmodule(UbTpBypass))
    assert "ta2tp_mode" not in src
    assert "op_len" not in src
    assert "rspst" not in src


def test_tx_payload_passthrough_no_tph():
    m = UbTpBypass()
    payload = _flits(0x111, 0x222, 0x333)
    pkt = m.submit(_op(dcna=0x55AA), payload, _sb())
    assert pkt.flits == payload
    assert [f.data for f in pkt.flits] == [0x111, 0x222, 0x333]
    assert pkt.bypass is True
    assert pkt.cfg == CFG_BYPASS
    assert pkt.dcna == 0x55AA


def test_tx_maps_ta_dcna_and_copies_sidebands():
    m = UbTpBypass()
    sb = _sb(sl=9, nlp=6, lbf=0xA5, rt=2, cci=0xBEEF)
    pkt = m.submit(_op(dcna=0x1234), _flits(0x1), sb)
    assert pkt.dcna == 0x1234
    assert pkt.sl == 9
    assert pkt.nlp == 6
    assert pkt.lbf == 0xA5
    assert pkt.rt == 2
    assert pkt.cci == 0xBEEF
    beats = list(iter_tx_beats(pkt))
    assert len(beats) == 1
    assert beats[0]["tp2nw_bypass"] == 1
    assert beats[0]["tp2nw_dcna"] == 0x1234
    assert beats[0]["tp2nw_sl"] == 9
    assert beats[0]["tp2nw_nlp"] == 6


def test_single_flit_sop_and_eop_legal():
    flits = check_payload(_flits(0xABCDEF))
    assert flits[0].sop and flits[0].eop
    m = UbTpBypass()
    pkt = m.submit(_op(), flits, _sb())
    assert pkt.flits[0].sop and pkt.flits[0].eop


def test_multi_flit_contiguous():
    payload = _flits(1, 2, 3, 4)
    assert [f.sop for f in payload] == [True, False, False, False]
    assert [f.eop for f in payload] == [False, False, False, True]
    m = UbTpBypass()
    pkt = m.submit(_op(), payload, _sb())
    assert len(list(iter_tx_beats(pkt))) == 4


def test_insert_sop_inside_packet_rejected():
    bad = (
        Flit(1, sop=True, eop=False),
        Flit(2, sop=True, eop=False),
        Flit(3, sop=False, eop=True),
    )
    with pytest.raises(UbTpBypassError, match="sop inside"):
        check_payload(bad)


def test_submit_requires_bypass():
    m = UbTpBypass()
    with pytest.raises(UbTpBypassError, match="ta2tp_bypass"):
        m.submit(_op(bypass=False), _flits(1), _sb())


def test_link_down_blocks_tx():
    m = UbTpBypass()
    m.submit(_op(tassn=3), _flits(1), _sb())
    fails = m.apply_link_down()
    assert len(fails) == 1
    assert fails[0].fail is True and fails[0].done is False
    assert fails[0].tassn == 3
    assert m.pending_tassn == frozenset()
    with pytest.raises(UbTpBypassError, match="nw_link_up"):
        m.submit(_op(tassn=4), _flits(2), _sb())


def test_flush_fails_every_pending_tassn():
    m = UbTpBypass()
    m.submit(_op(tassn=1), _flits(1), _sb(), tpmsn=7)
    m.submit(_op(tassn=2), _flits(2), _sb(), tpmsn=8)
    done = m.complete(1)
    assert done.done is True and done.fail is False
    assert done.tpmsn == 7
    fails = m.apply_flush()
    assert [c.tassn for c in fails] == [2]
    assert fails[0].fail is True
    assert fails[0].tpmsn == 8
    assert m.pending_tassn == frozenset()
    m.end_flush()
    assert m.flush is False


def test_flush_blocks_new_packet_until_cleared():
    m = UbTpBypass()
    m.apply_flush()
    with pytest.raises(UbTpBypassError, match="flush"):
        m.submit(_op(), _flits(1), _sb())
    m.end_flush()
    pkt = m.submit(_op(), _flits(1), _sb())
    assert pkt.bypass is True


def test_rx_payload_passthrough_and_err_on_eop():
    m = UbTpBypass()
    payload = _flits(0xA, 0xB)
    got = m.receive(payload, err=True, tassn=9, tpmsn=0x100)
    assert got is not None
    assert got.flits == payload
    assert got.err is True
    assert got.tassn == 9
    assert got.tpmsn == 0x100
    assert got.flits[-1].eop
    assert m.nw2tp_icrc_err == 0


def test_icrc_err_stays_zero_in_cfg9():
    m = UbTpBypass()
    m.receive(_flits(1), err=False)
    assert m.nw2tp_icrc_err == 0
    m.nw2tp_icrc_err = 1
    m.receive(_flits(2), err=True)
    assert m.nw2tp_icrc_err == 0


def test_drop_discards_rx_packet():
    m = UbTpBypass()
    assert m.receive(_flits(0x55), drop=True, err=True) is None
    keep = m.receive(_flits(0x66), drop=False)
    assert keep is not None
    assert keep.flits[0].data == 0x66
    assert keep.err is False


def test_apply_drop_fails_pending_tx():
    m = UbTpBypass()
    m.submit(_op(tassn=11), _flits(1), _sb())
    c = m.apply_drop(11)
    assert c.fail is True and c.done is False
    assert c.tassn == 11
    assert m.pending_tassn == frozenset()


def test_done_and_fail_mutex():
    with pytest.raises(UbTpBypassError, match="mutex"):
        TaComplete(tassn=1, done=True, fail=True)
    with pytest.raises(UbTpBypassError, match="mutex"):
        TaComplete(tassn=1, done=False, fail=False)


def test_complete_unknown_tassn_raises():
    m = UbTpBypass()
    with pytest.raises(UbTpBypassError, match="not pending"):
        m.complete(1)


def test_duplicate_pending_tassn_rejected():
    m = UbTpBypass()
    m.submit(_op(tassn=4), _flits(1), _sb())
    with pytest.raises(UbTpBypassError, match="already pending"):
        m.submit(_op(tassn=4), _flits(2), _sb())


def test_field_widths_rejected():
    with pytest.raises(UbTpBypassError, match="ta2tp_dcna"):
        TaOp(opcode=1, tassn=1, bypass=True, dcna=1 << 16)
    with pytest.raises(UbTpBypassError, match="tp2nw_sl"):
        NwTxSideband(sl=16, nlp=0, lbf=0, rt=0, cci=0)
    with pytest.raises(UbTpBypassError, match="data"):
        Flit(1 << 160, sop=True, eop=True)
    with pytest.raises(UbTpBypassError, match="tp2ta_tpmsn"):
        UbTpBypass().submit(_op(), _flits(1), _sb(), tpmsn=1 << 24)


def test_nlp_is_opaque_three_bits():
    # NLP→TAH codepoint is unknown; any 3-bit value is stored as-is.
    for nlp in range(8):
        pkt = UbTpBypass().submit(_op(tassn=nlp + 1), _flits(1), _sb(nlp=nlp))
        assert pkt.nlp == nlp


def test_reset_clears_pending_and_reopens_link():
    m = UbTpBypass()
    m.submit(_op(tassn=1), _flits(1), _sb())
    m.apply_link_down()
    m.reset()
    assert m.pending_tassn == frozenset()
    assert m.nw_link_up is True
    assert m.flush is False
    pkt = m.submit(_op(tassn=1), _flits(9), _sb())
    assert pkt.flits[0].data == 9


def test_end_flush_requires_empty_pending():
    m = UbTpBypass()
    m.submit(_op(tassn=1), _flits(1), _sb())
    m.flush = True
    with pytest.raises(UbTpBypassError, match="flush ends"):
        m.end_flush()
    m.complete(1, fail=True)
    m.end_flush()


def test_empty_payload_rejected():
    with pytest.raises(UbTpBypassError, match="empty"):
        check_payload(())
