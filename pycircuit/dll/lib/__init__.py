"""Helpers only — not SPEC §2.2 leaves. Gate scans pycircuit/<layer>/*.py."""

from dll.lib.bcrc_hw import bits_or_reduce, drive_gen, next_crc_hw
from dll.lib.bcrc_matrix import CRC_W, FLIT_W, INIT, WORD_W, next_crc

__all__ = [
    "CRC_W",
    "FLIT_W",
    "INIT",
    "WORD_W",
    "bits_or_reduce",
    "drive_gen",
    "next_crc",
    "next_crc_hw",
]
