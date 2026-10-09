"""Scrambler interface. Algorithm skipped until SPEC §13 closes taps / LID seed."""

from __future__ import annotations

import pytest

from tb.models.config import PENDING_SPEC
from tb.models.ub_pcs_scrambler import (
    AMCTL_LID_NULL,
    SymbolKind,
    UbPcsScrambler,
    UbPcsScramblerConfig,
)

SKIP_REASON = (
    "pending SPEC: PRBS23 taps and AMCTL.LID seed map (SPEC §13); "
    "do not invent PR #5 / Switch defaults"
)


def test_seed_source_is_amctl_lid_not_phys_or_ltb():
    scr = UbPcsScrambler(amctl_lid=3)
    assert scr.seed_source_is_amctl_lid()
    assert scr.amctl_lid == 3
    assert scr.amctl_lid != AMCTL_LID_NULL


def test_closed_widths_and_latency():
    cfg = UbPcsScramblerConfig()
    assert cfg.data_w == 32
    assert cfg.scr_w == 23
    assert cfg.lsb_first is True
    assert cfg.latency_cycles == 1


def test_exempt_kinds_are_not_scrambled():
    scr = UbPcsScrambler()
    assert not scr.should_scramble(SymbolKind.AMCTL)
    assert not scr.should_scramble(SymbolKind.EEIB)
    assert scr.should_scramble(SymbolKind.LTB)
    assert scr.should_scramble(SymbolKind.DLL)


def test_process_raises_pending_spec():
    scr = UbPcsScrambler()
    with pytest.raises(NotImplementedError, match=PENDING_SPEC):
        scr.process_symbol(0x00, SymbolKind.DLL)
    with pytest.raises(NotImplementedError, match=PENDING_SPEC):
        scr.process_word(0, en=True)
    with pytest.raises(NotImplementedError, match=PENDING_SPEC):
        scr.load_seed_from_amctl_lid(0)


@pytest.mark.skip(reason=SKIP_REASON)
def test_scramble_then_descramble_restores():
    raise NotImplementedError(PENDING_SPEC)


@pytest.mark.skip(reason=SKIP_REASON)
def test_lsb_first_step():
    raise NotImplementedError(PENDING_SPEC)
