"""BCRC properties. UB-DL §4.3.2.2.4 / §4.7.2. No numeric vector table in those sections."""

from __future__ import annotations

import random

import pytest

from tb.models.bcrc import BCRC_BYTES, FLIT_BYTES, Bcrc, pack_bcrc_word


def _rand_flits(n: int, seed: int = 0) -> list[int]:
    rng = random.Random(seed)
    # 160-bit flits; last 4 bytes left as don't-care (attach overwrites them)
    return [rng.getrandbits(8 * FLIT_BYTES) for _ in range(n)]


@pytest.mark.parametrize("n_flits", [1, 2, 8, 32])
def test_attach_then_check_passes(n_flits):
    bcrc = Bcrc()
    flits = bcrc.attach(_rand_flits(n_flits, n_flits))
    assert bcrc.check(flits)


def test_single_bit_flip_fails():
    bcrc = Bcrc()
    flits = bcrc.attach(_rand_flits(4, 99))
    mutated = list(flits)
    mutated[0] ^= 1  # flip LSB of first flit (payload, not BCRC)
    assert not bcrc.check(mutated)


def test_crc30_field_flip_fails():
    bcrc = Bcrc()
    flits = bcrc.attach(_rand_flits(1, 7))
    mutated = list(flits)
    mutated[-1] ^= 1  # likely hits a CRC30 bit in the last byte
    assert not bcrc.check(mutated)


def test_error_flag_is_in_bit30():
    word = pack_bcrc_word(0x15555555, error_flag=1, reserved=0)
    assert (word >> 30) & 1 == 1
    assert (word >> 31) & 1 == 0
    assert word & 0x3FFFFFFF == 0x15555555


def test_error_flag_changes_crc_when_included():
    bcrc = Bcrc()
    raw = _rand_flits(3, 3)
    a = bcrc.attach(raw, error_flag=0)
    b = bcrc.attach(raw, error_flag=1)
    crc_a, flag_a, _ = bcrc.extract(a)
    crc_b, flag_b, _ = bcrc.extract(b)
    assert flag_a == 0 and flag_b == 1
    assert crc_a != crc_b
    assert bcrc.check(a) and bcrc.check(b)


def test_init_all_ones_empty_body_is_not_zero():
    # One flit, all-zero payload, BCRC attached. Init = all 1s, not inverted.
    bcrc = Bcrc()
    attached = bcrc.attach([0])
    crc30, _, _ = bcrc.extract(attached)
    assert crc30 != 0
    assert bcrc.check(attached)


def test_deterministic_regression_vector():
    """Project-local lock vector — not a spec table (UB-DL §4.7.2 has none)."""
    bcrc = Bcrc()
    flit = 0
    for i, b in enumerate(bytes(range(16))):
        flit |= b << (8 * i)
    attached = bcrc.attach([flit], error_flag=0)
    crc30, flag, reserved = bcrc.extract(attached)
    assert flag == 0 and reserved == 0
    expected = bcrc.crc30_of_flits([flit], error_flag=0)
    assert crc30 == expected
    # Hard lock so a silent poly change fails CI. Not a spec table.
    assert expected == 0x0BE3426A
