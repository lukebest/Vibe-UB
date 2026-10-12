"""Golden rules for TP/TA contract fields. No RTL. 0 skip."""

from __future__ import annotations

import pytest

from tb.contracts.model import (
    CFG9,
    CFG9_FORBIDDEN,
    CFG_BYP,
    CFG_CTP,
    CFG_RTP,
    CFG_W,
    CLOSED_FROM_59,
    DCNA_W,
    FLIT_W,
    HDR_COMPACT,
    HDR_FULL,
    INI_TASSN_W,
    LPH_NTH_BYTES,
    MTU_DEFAULT,
    MTU_LEGAL,
    PENDING_XIA,
    PSN_MASK,
    PSN_W,
    RT_W,
    RTPH_BYTES,
    TP_TIMERS,
    TPMSN_W,
    UNKNOWN_XIA,
    VL_REQ,
    VL_RESP,
    bypass_cfg_ok,
    cfg9_forbidden_headers,
    cfg_encoding_ok,
    compact_header,
    done_fail_ok,
    extract_rt,
    header_bytes,
    icrc_forbidden,
    icrc_on_cfg,
    mtu_ok,
    predict_flit,
    predict_op,
    psn_next,
    psn_wraps,
    tp_timer_ok,
    vl_for_dir,
)


def test_psn_24bit_wrap():
    assert PSN_W == 24
    assert psn_next(PSN_MASK) == 0
    assert psn_wraps(PSN_MASK) is True
    assert psn_next(0) == 1
    assert psn_wraps(0) is False
    assert psn_next(0xFFFFFE) == 0xFFFFFF


def test_rtph_is_16_bytes():
    assert RTPH_BYTES == 16


def test_lph_nth_is_12_bytes():
    assert LPH_NTH_BYTES == 12


def test_ini_tassn_16bit():
    assert INI_TASSN_W == 16
    op = predict_op(opcode=1, tassn=0x1_0000, mode=0, bypass=1)
    assert op["tassn"] == 0
    assert op["tassn_w"] == 16


def test_mtu_legal_set_and_default():
    assert MTU_DEFAULT == 4096
    assert MTU_LEGAL == frozenset({1024, 4096, 8192})
    for mtu in MTU_LEGAL:
        assert mtu_ok(mtu)
    assert mtu_ok(2048) is False


def test_vl0_request_vl1_response():
    assert vl_for_dir("req") == VL_REQ == 0
    assert vl_for_dir("resp") == VL_RESP == 1


def test_cfg9_compact_headers():
    assert compact_header(CFG9) is True
    assert header_bytes("BTAH", CFG9) == 4
    assert header_bytes("ATAH", CFG9) == 4
    assert header_bytes("MAETAH", CFG9) == 12
    assert HDR_COMPACT["BTAH"] == 4
    assert HDR_COMPACT["MAETAH"] == 12


@pytest.mark.parametrize("cfg", [0, 1, 6, 8, 10, 15])
def test_non_cfg9_full_headers(cfg):
    if cfg == CFG9:
        pytest.fail("CFG9 is compact, not this case")
    assert compact_header(cfg) is False
    assert header_bytes("BTAH", cfg) == 8
    assert header_bytes("ATAH", cfg) == 8
    assert header_bytes("MAETAH", cfg) == 16
    assert HDR_FULL["BTAH"] == 8
    assert HDR_FULL["MAETAH"] == 16


def test_cfg9_forbids_icrc_tph_eidh_upih():
    assert cfg9_forbidden_headers(CFG9) == CFG9_FORBIDDEN
    assert cfg9_forbidden_headers(6) == frozenset()


def test_bypass_only_cfg9():
    assert bypass_cfg_ok(1, CFG9) is True
    assert bypass_cfg_ok(1, 6) is False
    assert bypass_cfg_ok(0, 6) is True


def test_flit_width_and_one_beat():
    beat = predict_flit(data=(1 << 160) | 0x5, sop=1, eop=1, sl=1, nlp=2, bypass=1)
    assert beat["flit_w"] == FLIT_W == 160
    assert beat["flits_per_beat"] == 1
    assert beat["data"] == 0x5
    assert beat["sop"] == 1 and beat["eop"] == 1


def test_done_fail_mutex():
    assert done_fail_ok(1, 0) is True
    assert done_fail_ok(0, 1) is True
    assert done_fail_ok(0, 0) is True
    assert done_fail_ok(1, 1) is False


def test_extract_rt_is_two_bits():
    # Width locked at 2 b (LAYER_CONTRACTS §2). Slice index stays unknown.
    assert RT_W == 2
    word = 0x3 << 4
    assert extract_rt(word, 4) == 0x3
    assert extract_rt(word, 0) == 0


def test_closed_from_59_and_ten_unknowns():
    assert len(CLOSED_FROM_59) == 4
    assert any("DCNA 16" in item for item in CLOSED_FROM_59)
    assert any("ICRC on CFG7" in item for item in CLOSED_FROM_59)
    assert any("CTP=6" in item for item in CLOSED_FROM_59)
    assert any("LPH.RT 2 b" in item for item in CLOSED_FROM_59)
    assert len(UNKNOWN_XIA) == 10
    assert PENDING_XIA == UNKNOWN_XIA
    assert any("NLP" in item for item in UNKNOWN_XIA)
    assert any("Go-Back-N" in item for item in UNKNOWN_XIA)
    assert not any("CFG6" in item for item in UNKNOWN_XIA)


def test_dcna_16_and_cfg_encoding():
    assert DCNA_W == 16
    assert CFG_W == 4
    assert CFG_CTP == 6 and CFG_RTP == 7 and CFG_BYP == 9
    assert cfg_encoding_ok(6) and cfg_encoding_ok(7) and cfg_encoding_ok(9)
    assert cfg_encoding_ok(0) is False
    beat = predict_flit(data=1, sop=1, eop=1, dcna=0x1_0000)
    assert beat["dcna"] == 0


def test_icrc_on_cfg7_not_cfg9():
    assert icrc_on_cfg(CFG_RTP) is True
    assert icrc_on_cfg(CFG_BYP) is False
    assert icrc_forbidden(CFG_BYP) is True
    assert icrc_forbidden(CFG_RTP) is False
    assert icrc_on_cfg(CFG_CTP) is False


def test_tp_owns_rto_and_ack_coal_only():
    assert TP_TIMERS == frozenset({"rto", "ack_coal"})
    assert tp_timer_ok("rto")
    assert tp_timer_ok("ack_coal")
    assert tp_timer_ok("retry_wait") is False
    assert tp_timer_ok("probe_wait") is False


def test_tpmsn_24bit():
    assert TPMSN_W == 24
