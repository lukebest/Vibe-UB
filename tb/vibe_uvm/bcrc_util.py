"""BCRC stream helpers. Goldens come only from tb.vibe_uvm.golden."""

from __future__ import annotations

from tb.vibe_uvm.golden import bcrc as BM

FLIT_W = 160
CRC_MASK = 0x3FFFFFFF


def payload_flit(payload16: list[int], word: int = 0) -> int:
    if len(payload16) != 16:
        raise ValueError(payload16)
    return BM.bytes_to_flit(payload16 + BM.word_to_le_bytes(word))


def attach(flits: list[int], *, error_flag: int = 0, reserved: int = 0) -> list[int]:
    return BM.UbDllBcrc().attach(flits, error_flag=error_flag, reserved=reserved)


def crc30_of(flits: list[int]) -> int:
    return BM.UbDllBcrc().crc30_of_flits(flits)


def pack_word(crc30: int, error_flag: int = 0, reserved: int = 0) -> int:
    return BM.pack_bcrc_word(crc30, error_flag, reserved)


def extract_word(flit: int) -> int:
    last = BM.flit_to_bytes(flit)
    return BM.le_bytes_to_word(last[-4:])
