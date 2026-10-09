"""BCRC interface. Compute skipped until SPEC; packing is the known constraint."""

from __future__ import annotations

import pytest

from tb.models.config import PENDING_SPEC
from tb.models.ub_dll_bcrc import LATENCY_CYCLES, UbDllBcrc, UbDllBcrcConfig, pack_bcrc_word, unpack_bcrc_word

SKIP_REASON = (
    "pending SPEC: BCRC poly / init / invert / bit-order; "
    "do not copy PR #5 / Switch"
)


def test_pack_is_rsvd_error_flag_crc30():
    word = pack_bcrc_word(0x15555555, error_flag=1, reserved=0)
    assert (word >> 30) & 1 == 1
    assert (word >> 31) & 1 == 0
    assert word & 0x3FFFFFFF == 0x15555555
    crc30, flag, reserved = unpack_bcrc_word(word)
    assert (crc30, flag, reserved) == (0x15555555, 1, 0)


def test_config_has_no_poly_or_init_default():
    cfg = UbDllBcrcConfig()
    assert cfg.word_w == 32
    assert cfg.latency_cycles == LATENCY_CYCLES == 1
    assert not hasattr(cfg, "poly")
    assert not hasattr(cfg, "init")


def test_compute_raises_pending_spec():
    bcrc = UbDllBcrc()
    with pytest.raises(NotImplementedError, match=PENDING_SPEC):
        bcrc.crc30_of_flits([0])
    with pytest.raises(NotImplementedError, match=PENDING_SPEC):
        bcrc.attach([0])
    with pytest.raises(NotImplementedError, match=PENDING_SPEC):
        bcrc.check([0])


@pytest.mark.skip(reason=SKIP_REASON)
def test_attach_then_check_passes():
    raise NotImplementedError(PENDING_SPEC)


@pytest.mark.skip(reason=SKIP_REASON)
def test_single_bit_flip_fails():
    raise NotImplementedError(PENDING_SPEC)
