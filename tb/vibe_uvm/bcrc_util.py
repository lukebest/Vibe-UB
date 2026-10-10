"""BCRC stream helpers. Goldens come only from tb.vibe_uvm.golden.

``crc30_spec`` is a second implementation of SPEC §2.6 (poly/init/MSB-first)
so a bug in ``UbDllBcrc`` cannot silently agree with itself.
"""

from __future__ import annotations

from tb.vibe_uvm.golden import bcrc as BM

FLIT_W = 160
CRC_MASK = 0x3FFFFFFF
CRC30_POLY = 0x15A94AD5
CRC30_INIT = 0x3FFFFFFF


def payload_flit(payload16: list[int], word: int = 0) -> int:
    if len(payload16) != 16:
        raise ValueError(payload16)
    return BM.bytes_to_flit(payload16 + BM.word_to_le_bytes(word))


def attach(flits: list[int], *, error_flag: int = 0, reserved: int = 0) -> list[int]:
    return BM.UbDllBcrc().attach(flits, error_flag=error_flag, reserved=reserved)


def crc30_spec(flits: list[int]) -> int:
    """SPEC §2.6: poly 30'h15A94AD5, init all-1s, byte-upward MSB-first, no invert.

    The last four bytes of the last flit are the BCRC word and are not in the CRC.
    """
    crc = CRC30_INIT
    raw: list[int] = []
    for flit in flits:
        raw.extend(BM.flit_to_bytes(flit))
    for byte in raw[:-4]:
        for shift in range(7, -1, -1):
            bit = (byte >> shift) & 1
            msb = (crc >> 29) & 1
            crc = ((crc << 1) & CRC_MASK) ^ (CRC30_POLY if (msb ^ bit) else 0)
    return crc


def crc30_of(flits: list[int]) -> int:
    model = BM.UbDllBcrc().crc30_of_flits(flits)
    spec = crc30_spec(flits)
    if model != spec:
        raise AssertionError(f"BCRC golden split: model=0x{model:08x} spec=0x{spec:08x}")
    return spec


def pack_word(crc30: int, error_flag: int = 0, reserved: int = 0) -> int:
    return BM.pack_bcrc_word(crc30, error_flag, reserved)


def extract_word(flit: int) -> int:
    last = BM.flit_to_bytes(flit)
    return BM.le_bytes_to_word(last[-4:])
