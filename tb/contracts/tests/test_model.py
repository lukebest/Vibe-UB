"""Golden rules for TP/TA contract fields. No RTL. 0 skip."""

from __future__ import annotations

import math

import pytest

from tb.contracts.model import (
    CFG9,
    CFG9_FORBIDDEN,
    F_CORE_HZ,
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
    RTPH_BYTES,
    TIMEOUT_DEFAULT_CYC,
    TIMEOUT_US,
    VL_REQ,
    VL_RESP,
    bypass_cfg_ok,
    cfg9_forbidden_headers,
    compact_header,
    done_fail_ok,
    extract_rt,
    header_bytes,
    mtu_ok,
    predict_flit,
    predict_op,
    psn_next,
    psn_wraps,
    timed_out,
    timeout_cycles,
    vl_for_dir,
)


def test_f_core_and_timeout_default():
    assert TIMEOUT_DEFAULT_CYC == 323
    assert math.ceil(TIMEOUT_US * 1e-6 * F_CORE_HZ) == 323
    assert timeout_cycles(None) == 323
    assert timeout_cycles(0) == 323
    assert timeout_cycles(323) == 323


def test_timeout_cycle_322_not_fired():
    assert timed_out(322, 323) is False
    assert timed_out(322) is False


def test_timeout_cycle_323_fired():
    assert timed_out(323, 323) is True
    assert timed_out(323) is True
    assert timed_out(324) is True


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


def test_extract_rt_uses_caller_slice():
    # Bit index is 待 Xia; the helper only shifts a 2-bit RT.
    word = 0x3 << 4
    assert extract_rt(word, 4) == 0x3
    assert extract_rt(word, 0) == 0


def test_pending_xia_is_nonempty():
    assert PENDING_XIA
    assert any("NLP" in item for item in PENDING_XIA)
    assert any("Go-Back-N" in item for item in PENDING_XIA)
