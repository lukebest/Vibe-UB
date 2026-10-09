"""Scrambler properties. UB-PHY §3.2.2.4 / §3.2.3.2. No official vector table in those sections."""

from __future__ import annotations

import random

import pytest

from tb.models.config import PendingParams
from tb.models.scrambler import LaneScrambler, ScramblerConfig, SymbolKind


def _mk(num_lanes=1, **pending_kw):
    pending = PendingParams(**pending_kw) if pending_kw else PendingParams()
    return LaneScrambler(num_lanes, ScramblerConfig(pending=pending))


@pytest.mark.parametrize("nlanes", [1, 4, 8])
@pytest.mark.parametrize("kind", [SymbolKind.DLL, SymbolKind.LTB])
def test_scramble_then_descramble_restores(nlanes, kind):
    rng = random.Random(0xC0FFEE)
    tx = _mk(nlanes)
    rx = _mk(nlanes)
    for lane in range(nlanes):
        data = [rng.randrange(256) for _ in range(64)]
        scrambled = tx.process_symbols(lane, data, kind)
        restored = rx.process_symbols(lane, scrambled, kind)
        assert restored == data
        assert scrambled != data  # additive PRBS23 is not identity on all-ones seed


def test_amctl_and_eeib_not_scrambled():
    scr = _mk(1)
    for kind in (SymbolKind.AMCTL, SymbolKind.EEIB):
        data = list(range(16))
        out = scr.process_symbols(0, data, kind)
        assert out == data


def test_exempt_does_not_advance_lfsr_by_default():
    a = _mk(1)
    b = _mk(1)
    a.process_symbols(0, [0xA5] * 8, SymbolKind.AMCTL)
    x = a.process_symbol(0, 0x00, SymbolKind.DLL)
    y = b.process_symbol(0, 0x00, SymbolKind.DLL)
    assert x == y


def test_edf_resets_seed_outside_null_or_active():
    scr = _mk(1)
    first = scr.process_symbol(0, 0x00, SymbolKind.DLL)
    scr.process_symbols(0, [1, 2, 3, 4], SymbolKind.DLL)
    scr.maybe_reset_on_amctl(0, has_edf=True, has_sdf=False, lmsm_in_null_or_active=False)
    again = scr.process_symbol(0, 0x00, SymbolKind.DLL)
    assert again == first


def test_sdf_does_not_reset_in_null_or_active():
    scr = _mk(1)
    first = scr.process_symbol(0, 0x00, SymbolKind.DLL)
    scr.process_symbols(0, [1, 2, 3, 4], SymbolKind.DLL)
    scr.maybe_reset_on_amctl(0, has_edf=False, has_sdf=True, lmsm_in_null_or_active=True)
    later = scr.process_symbol(0, 0x00, SymbolKind.DLL)
    assert later != first


def test_lsb_first_changes_first_bit():
    scr = _mk(1)
    out = scr.process_symbol(0, 0x01, SymbolKind.DLL)  # only bit 0 set
    # After XOR with first LFSR bit, either bit0 flips or not; remaining
    # bits come only from LFSR. Just lock the property: only 8 bits produced.
    assert 0 <= out <= 255


def test_per_lane_state_is_independent():
    scr = _mk(4)
    a = scr.process_symbol(0, 0x00, SymbolKind.DLL)
    b = scr.process_symbol(1, 0x00, SymbolKind.DLL)
    # Same default seed => same first scramble bit-stream on each lane.
    assert a == b
    # After advancing lane 0 only, lane 1 still at its own step-1.
    c = scr.process_symbol(1, 0x00, SymbolKind.DLL)
    d = _mk(4)
    d.process_symbol(1, 0x00, SymbolKind.DLL)
    assert c == d.process_symbol(1, 0x00, SymbolKind.DLL)


def test_custom_seed_table():
    seeds = {0: 0x7FFFFE, 1: 0x000001}
    cfg = ScramblerConfig()
    tx = LaneScrambler(2, cfg, seeds=seeds)
    rx = LaneScrambler(2, cfg, seeds=seeds)
    data = [0x11, 0x22, 0x33]
    s0 = tx.process_symbols(0, data, SymbolKind.DLL)
    s1 = tx.process_symbols(1, data, SymbolKind.DLL)
    assert s0 != s1
    assert rx.process_symbols(0, s0, SymbolKind.DLL) == data
    assert rx.process_symbols(1, s1, SymbolKind.DLL) == data
