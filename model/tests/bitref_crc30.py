"""Independent bit-by-bit CRC30. Not imported by ``model.ub_dll_bcrc``.

SPEC §2.6 / UB-DL §4.7.2 (project restatement, no spec text):
init all-1s; each input bit MSB-first per byte from Byte 0; remainder not
inverted or reflected. Polynomial tap mask ``30'h15A94AD5`` (``x^30`` implicit).
"""

from __future__ import annotations

# Local copy of the closed tap mask so this file does not import the model.
_CRC30_POLY = 0x15A94AD5
_CRC30_WIDTH = 30


def crc30_bits(bits: list[int]) -> int:
    """Shift a 30-bit register one data bit at a time.

    ``reg[0]`` is the MSB (the bit that would leave as x^30). Mix = MSB xor
    data; then shift toward the MSB and XOR the tap mask when mix is 1.
    """
    if any(b not in (0, 1) for b in bits):
        raise ValueError("bits must be 0/1")
    reg = [1] * _CRC30_WIDTH
    tap = [(_CRC30_POLY >> i) & 1 for i in range(_CRC30_WIDTH)]
    for bit in bits:
        mix = reg[0] ^ bit
        reg = reg[1:] + [0]
        if mix:
            for i in range(_CRC30_WIDTH):
                if tap[i]:
                    reg[_CRC30_WIDTH - 1 - i] ^= 1
    crc = 0
    for i, b in enumerate(reg):
        crc |= b << (_CRC30_WIDTH - 1 - i)
    return crc


def bytes_to_msb_first_bits(data: list[int]) -> list[int]:
    """Byte 0 first; within each byte bit7 then bit6 … bit0 (SPEC §2.6)."""
    bits: list[int] = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits


def crc30_bitref(data: list[int]) -> int:
    """Byte-list wrapper around :func:`crc30_bits`."""
    return crc30_bits(bytes_to_msb_first_bits(data))
