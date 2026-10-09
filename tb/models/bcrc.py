"""DLL BCRC (CRC30 + 2 info bits).

Normative: UB-DL §4.3.2.2.4 (field), §4.7.2 (CRC check).
Project: SPEC §2.6, §3.2.2, §7. 32-bit word at the end of each DLLDB.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tb.models.config import PENDING, PendingParams

# UB-DL §4.7.2 polynomial:
# x^30 + x^28 + x^26 + x^24 + x^23 + x^21 + x^19 + x^16 + x^14
# + x^11 + x^9 + x^7 + x^6 + x^4 + x^2 + 1
# Remainder taps (x^29..x^0), x^30 implicit:
CRC30_POLY = 0x15A94AD5
CRC30_INIT = 0x3FFFFFFF  # UB-DL §4.7.2: initial value all 1s
CRC30_MASK = 0x3FFFFFFF
FLIT_BYTES = 20  # SPEC §9 FLIT_W = 160
BCRC_BYTES = 4


@dataclass
class BcrcConfig:
    pending: PendingParams = field(default_factory=lambda: PENDING)
    poly: int = CRC30_POLY
    init: int = CRC30_INIT
    flit_bytes: int = FLIT_BYTES


def _update_bit(crc: int, bit: int, poly: int) -> int:
    msb = (crc >> 29) & 1
    crc = ((crc << 1) & CRC30_MASK)
    if msb ^ (bit & 1):
        crc ^= poly
    return crc


def _update_byte(crc: int, byte: int, poly: int) -> int:
    # UB-DL §4.7.2: Byte 0 Bit 7, then Byte 0 Bit 6, ...
    for shift in range(7, -1, -1):
        crc = _update_bit(crc, (byte >> shift) & 1, poly)
    return crc


def flit_to_bytes(flit: int, n: int = FLIT_BYTES) -> list[int]:
    """Project little-endian: byte 0 = flit[7:0] (REGMAP / SPEC flit word)."""
    return [(flit >> (8 * i)) & 0xFF for i in range(n)]


def bytes_to_flit(data: list[int]) -> int:
    acc = 0
    for i, b in enumerate(data):
        acc |= (b & 0xFF) << (8 * i)
    return acc


def pack_bcrc_word(crc30: int, error_flag: int = 0, reserved: int = 0) -> int:
    """32-bit BCRC: bit[31]=Reserved, bit[30]=ERROR_FLAG, bit[29:0]=CRC30.

    UB-DL §4.3.2.2.4 / §4.7.2. Sender Reserved default 0.
    """
    return ((reserved & 1) << 31) | ((error_flag & 1) << 30) | (crc30 & CRC30_MASK)


def unpack_bcrc_word(word: int) -> tuple[int, int, int]:
    reserved = (word >> 31) & 1
    error_flag = (word >> 30) & 1
    crc30 = word & CRC30_MASK
    return crc30, error_flag, reserved


def _bcrc_bytes_from_word(word: int, msb_in_byte16: bool) -> list[int]:
    if msb_in_byte16:
        return [
            (word >> 24) & 0xFF,
            (word >> 16) & 0xFF,
            (word >> 8) & 0xFF,
            word & 0xFF,
        ]
    return [
        word & 0xFF,
        (word >> 8) & 0xFF,
        (word >> 16) & 0xFF,
        (word >> 24) & 0xFF,
    ]


def _word_from_bcrc_bytes(data: list[int], msb_in_byte16: bool) -> int:
    if msb_in_byte16:
        return (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
    return data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)


class Bcrc:
    def __init__(self, cfg: BcrcConfig | None = None) -> None:
        self.cfg = cfg or BcrcConfig()

    def crc30_of_flits(
        self,
        flits: list[int],
        *,
        error_flag: int = 0,
        reserved: int = 0,
    ) -> int:
        """CRC30 over a DLLDB (UB-DL §4.7.2). Last 30 bits of the last flit excluded."""
        if not flits:
            raise ValueError("DLLDB must contain at least one flit (UB-DL §4.3)")
        raw: list[int] = []
        for flit in flits:
            raw.extend(flit_to_bytes(flit, self.cfg.flit_bytes))
        body = raw[: -BCRC_BYTES]
        crc = self.cfg.init
        for byte in body:
            crc = _update_byte(crc, byte, self.cfg.poly)
        if self.cfg.pending.bcrc_include_info_bits:
            crc = _update_bit(crc, reserved & 1, self.cfg.poly)
            crc = _update_bit(crc, error_flag & 1, self.cfg.poly)
        return crc

    def attach(
        self,
        flits: list[int],
        *,
        error_flag: int = 0,
        reserved: int = 0,
    ) -> list[int]:
        """Write BCRC into the last flit's last 4 bytes. Returns a new list."""
        crc30 = self.crc30_of_flits(flits, error_flag=error_flag, reserved=reserved)
        word = pack_bcrc_word(crc30, error_flag, reserved)
        out = list(flits)
        last = flit_to_bytes(out[-1], self.cfg.flit_bytes)
        last[-BCRC_BYTES:] = _bcrc_bytes_from_word(word, self.cfg.pending.bcrc_byte16_is_msb)
        out[-1] = bytes_to_flit(last)
        return out

    def check(self, flits: list[int]) -> bool:
        """True when the stored CRC30 matches a recalculation (UB-DL §4.7.2)."""
        last = flit_to_bytes(flits[-1], self.cfg.flit_bytes)
        word = _word_from_bcrc_bytes(last[-BCRC_BYTES:], self.cfg.pending.bcrc_byte16_is_msb)
        stored, error_flag, reserved = unpack_bcrc_word(word)
        calc = self.crc30_of_flits(flits, error_flag=error_flag, reserved=reserved)
        return stored == calc

    def extract(self, flits: list[int]) -> tuple[int, int, int]:
        last = flit_to_bytes(flits[-1], self.cfg.flit_bytes)
        word = _word_from_bcrc_bytes(last[-BCRC_BYTES:], self.cfg.pending.bcrc_byte16_is_msb)
        return unpack_bcrc_word(word)
