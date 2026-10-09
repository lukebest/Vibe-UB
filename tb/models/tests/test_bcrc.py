"""BCRC properties against SPEC §2.6. Bit-serial reference is independent of the model."""

from __future__ import annotations

import pytest

from tb.models.ub_dll_bcrc import (
    BCRC_BYTES,
    CRC30_INIT,
    CRC30_MASK,
    CRC30_POLY,
    FLIT_BYTES,
    UbDllBcrc,
    bytes_to_flit,
    flit_to_bytes,
    pack_bcrc_word,
    unpack_bcrc_word,
)

def crc30_bitref(data: list[int]) -> int:
    """Bit-serial 30-bit register (index 0 = MSB). Not the model's integer CRC.

    Init all-1s; each byte bit7..bit0; mix = MSB xor data; shift toward MSB;
    XOR tap mask into the register when mix=1. Remainder not inverted.
    """
    reg = [1] * 30
    tap = [(CRC30_POLY >> i) & 1 for i in range(30)]
    for byte in data:
        for shift in range(7, -1, -1):
            mix = reg[0] ^ ((byte >> shift) & 1)
            reg = reg[1:] + [0]
            if mix:
                for i in range(30):
                    if tap[i]:
                        reg[29 - i] ^= 1
    crc = 0
    for i, bit in enumerate(reg):
        crc |= bit << (29 - i)
    return crc


def _flit_from_payload(payload: list[int]) -> int:
    if len(payload) != FLIT_BYTES - BCRC_BYTES:
        raise ValueError(payload)
    return bytes_to_flit(payload + [0] * BCRC_BYTES)


def test_pack_field_positions():
    word = pack_bcrc_word(0x15555555, error_flag=1, reserved=0)
    assert (word >> 31) & 1 == 0
    assert (word >> 30) & 1 == 1
    assert word & CRC30_MASK == 0x15555555
    crc30, flag, reserved = unpack_bcrc_word(word)
    assert (crc30, flag, reserved) == (0x15555555, 1, 0)
    word0 = pack_bcrc_word(0x0, error_flag=0, reserved=1)
    assert (word0 >> 31) & 1 == 1
    assert (word0 >> 30) & 1 == 0


@pytest.mark.parametrize(
    "payload",
    [
        [0x00] * 16,
        [0xFF] * 16,
        list(range(16)),
    ],
    ids=["all_zero", "all_one", "incrementing"],
)
def test_attach_matches_bitref_and_checks(payload):
    model = UbDllBcrc()
    flits = model.attach([_flit_from_payload(payload)])
    crc30, flag, reserved = model.extract(flits)
    assert flag == 0 and reserved == 0
    assert crc30 == crc30_bitref(payload)
    assert crc30 == model.crc30_of_bytes(payload)
    assert model.check(flits)
    last = flit_to_bytes(flits[-1])
    packed = last[-4] | (last[-3] << 8) | (last[-2] << 16) | (last[-1] << 24)
    assert packed == pack_bcrc_word(crc30, 0, 0)


def test_error_flag_is_packed_not_crced():
    model = UbDllBcrc()
    raw = [_flit_from_payload(list(range(16)))]
    a = model.attach(raw, error_flag=0)
    b = model.attach(raw, error_flag=1)
    crc_a, flag_a, _ = model.extract(a)
    crc_b, flag_b, _ = model.extract(b)
    assert flag_a == 0 and flag_b == 1
    assert crc_a == crc_b
    assert model.check(a) and model.check(b)


def test_single_bit_flip_is_detected():
    model = UbDllBcrc()
    flits = model.attach([_flit_from_payload([0x00] * 16)])
    mutated = [flits[0] ^ 1]
    assert not model.check(mutated)
    crc_flip = [flits[0] ^ (1 << (8 * 16))]
    assert not model.check(crc_flip)


def test_two_flits_cross_check():
    model = UbDllBcrc()
    first = bytes_to_flit(list(range(20)))
    second = _flit_from_payload([0xA5] * 16)
    attached = model.attach([first, second])
    body = flit_to_bytes(first) + [0xA5] * 16
    crc30, _, _ = model.extract(attached)
    assert crc30 == crc30_bitref(body)
    assert model.check(attached)


def test_eat_last_matches_block():
    model = UbDllBcrc()
    payload = list(range(16))
    flit = _flit_from_payload(payload)
    attached = model.attach([flit])
    stream = UbDllBcrc()
    crc30 = stream.eat(attached[0], last=True)
    assert crc30 == model.extract(attached)[0]
