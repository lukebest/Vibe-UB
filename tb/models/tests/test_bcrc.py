"""BCRC interface. Compute skipped until the golden is filled from SPEC, not PR #5."""

from __future__ import annotations

import pytest

from tb.models.config import PENDING_SPEC
from tb.models.ub_dll_bcrc import (
    LATENCY_CYCLES,
    SPEC_BCRC_INIT,
    SPEC_BCRC_POLY,
    UbDllBcrc,
    pack_bcrc_word,
    unpack_bcrc_word,
)

SKIP_REASON = (
    "pending SPEC: BCRC step not filled in this PR "
    "(do not copy PR #5 / Switch); packing is tested"
)


def test_pack_is_rsvd_error_flag_crc30():
    word = pack_bcrc_word(0x15555555, error_flag=1, reserved=0)
    assert (word >> 30) & 1 == 1
    assert (word >> 31) & 1 == 0
    assert word & 0x3FFFFFFF == 0x15555555
    crc30, flag, reserved = unpack_bcrc_word(word)
    assert (crc30, flag, reserved) == (0x15555555, 1, 0)


def test_spec_documents_poly_and_init_without_using_them():
    assert SPEC_BCRC_POLY == 0x15A94AD5
    assert SPEC_BCRC_INIT == 0x3FFFFFFF
    assert LATENCY_CYCLES == 1


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
