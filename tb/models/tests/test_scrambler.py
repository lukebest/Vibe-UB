"""Scrambler properties. §13 taps / LID→seed are explicit 示例, not SPEC defaults."""

from __future__ import annotations

import pytest

from tb.models.ub_pcs_scrambler import (
    AMCTL_LID_NULL,
    DATA_W,
    SCR_W,
    SymbolKind,
    UbPcsScrambler,
    UbPcsScramblerConfig,
)

# 示例 only (SPEC §13 still open). Not the PR #5 / Switch pair (23, 18)
# and not `{prefix=1, lid, 2'b01}`.
EXAMPLE_TAPS = (23, 5)
EXAMPLE_LID_TO_SEED = {
    lid: ((0x2A13 * (lid + 3)) ^ 0x10A5) & ((1 << SCR_W) - 1)
    for lid in range(9)
}


def _cfg() -> UbPcsScramblerConfig:
    return UbPcsScramblerConfig(poly_taps=EXAMPLE_TAPS, lid_to_seed=EXAMPLE_LID_TO_SEED)


def _mk(lid: int = 0) -> UbPcsScrambler:
    return UbPcsScrambler(_cfg(), amctl_lid=lid)


def test_required_params_have_no_defaults():
    with pytest.raises(TypeError):
        UbPcsScramblerConfig()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        UbPcsScramblerConfig(poly_taps=EXAMPLE_TAPS)  # type: ignore[call-arg]


def test_seed_source_is_amctl_lid_not_phys_or_ltb():
    scr = _mk(3)
    assert scr.seed_source_is_amctl_lid()
    assert scr.amctl_lid == 3
    assert scr.amctl_lid != AMCTL_LID_NULL
    assert scr.seed_of(3) == EXAMPLE_LID_TO_SEED[3]
    assert scr.seed_of(3) != EXAMPLE_LID_TO_SEED[0]


def test_closed_widths():
    cfg = _cfg()
    assert cfg.scr_w == 23
    assert cfg.data_w == DATA_W == 32
    assert cfg.lsb_first is True


def test_exempt_kinds_do_not_scramble_or_step():
    a = _mk(1)
    for kind in (SymbolKind.AMCTL, SymbolKind.EEIB):
        assert a.process_symbol(0xA5, kind) == 0xA5
    b = _mk(1)
    a.process_word(0xFFFFFFFF, en=False)
    x = a.process_symbol(0x00, SymbolKind.DLL)
    y = b.process_symbol(0x00, SymbolKind.DLL)
    assert x == y


def test_lsb_first_hits_bit0_before_bit7():
    """示例 taps: first LFSR bit XORs data[0], not data[7]."""
    z = _mk(2).process_symbol(0x00, SymbolKind.DLL)
    k0, k7 = z & 1, (z >> 7) & 1
    out_01 = _mk(2).process_symbol(0x01, SymbolKind.DLL)
    out_80 = _mk(2).process_symbol(0x80, SymbolKind.DLL)
    assert (out_01 & 1) == (1 ^ k0)
    assert (out_80 & 1) == k0
    assert (out_01 >> 7) & 1 == k7
    assert (out_80 >> 7) & 1 == (1 ^ k7)


def test_edf_reloads_seed_outside_null_or_active():
    scr = _mk(4)
    first = scr.process_symbol(0x00, SymbolKind.DLL)
    scr.process_symbol(0x22, SymbolKind.DLL)
    scr.maybe_reload_seed(has_edf=True, has_sdf=False, lmsm_in_null_or_active=False)
    again = scr.process_symbol(0x00, SymbolKind.DLL)
    assert again == first


def test_sdf_does_not_reload_in_null_or_active():
    scr = _mk(4)
    first = scr.process_symbol(0x00, SymbolKind.DLL)
    scr.process_symbol(0x22, SymbolKind.DLL)
    scr.maybe_reload_seed(has_edf=False, has_sdf=True, lmsm_in_null_or_active=True)
    later = scr.process_symbol(0x00, SymbolKind.DLL)
    assert later != first


def test_reseed_via_seed_load_changes_with_lid():
    scr = _mk(0)
    a = scr.process_word(0, en=True)
    scr.load_seed_from_amctl_lid(1)
    b = scr.process_word(0, en=True)
    other = _mk(1)
    assert b == other.process_word(0, en=True)
    assert a != b


def test_scramble_then_descramble_restores():
    tx = _mk(6)
    rx = _mk(6)
    words = [0x0, 0xFFFFFFFF, 0x12345678, 0xA5A5A5A5]
    for w in words:
        y = tx.process_word(w, en=True)
        assert rx.process_word(y, en=True) == w
        if w not in (0,):
            assert y != w
    tx2 = _mk(6)
    rx2 = _mk(6)
    data = [0x00, 0x01, 0x80, 0xFF, 0x5A]
    out = [tx2.process_symbol(s, SymbolKind.LTB) for s in data]
    back = [rx2.process_symbol(s, SymbolKind.LTB) for s in out]
    assert back == data
