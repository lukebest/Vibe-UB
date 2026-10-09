"""ub_dll_bcrc / ub_dll_bcrc_check (CODING_STYLE §5).

SPEC §2.6 (UB-DL §4.3.2.2.4 / §4.7.2):

- CRC30 poly ``x^30+x^28+x^26+x^24+x^23+x^21+x^19+x^16+x^14+x^11+x^9+x^7+x^6+x^4+x^2+1``
  30-bit tap mask ``30'h15A94AD5`` (``x^30`` implicit).
- Init all-1s. Remainder not inverted, not reordered.
- From DLLDB Byte 0 upward; each byte MSB first.
- Covers all data before the CRC30 field. This model treats the last 4 bytes
  of the last 160-bit flit as the 32-bit BCRC word and CRCs every prior byte.
  ERROR_FLAG is packed after the remainder and is not compared
  (SPEC: 检查口只比对 30-bit CRC30；ERROR_FLAG 不参与 CRC 符合性).
- Pack ``{1'b0, ERROR_FLAG, crc[29:0]}``. Word bit0 sits at the LSB of those
  4 bytes (flit bit0 = LSB, SPEC §3.3).
"""

from __future__ import annotations

from dataclasses import dataclass

CRC30_POLY = 0x15A94AD5
CRC30_INIT = 0x3FFFFFFF
CRC30_MASK = 0x3FFFFFFF
FLIT_W = 160
FLIT_BYTES = 20
BCRC_BYTES = 4
WORD_W = 32
LATENCY_CYCLES = 1

LEAF_PORTS = (
    "core_clk",
    "rst_pyc",
    "start",
    "valid_in",
    "data_in",
    "last",
    "error_flag",
    "crc_word",
    "done",
)
LEAF_CHECK_PORTS = LEAF_PORTS + ("crc_recv", "crc_ok", "crc_fail")


@dataclass
class UbDllBcrcConfig:
    poly: int = CRC30_POLY
    init: int = CRC30_INIT
    flit_bytes: int = FLIT_BYTES
    word_w: int = WORD_W
    latency_cycles: int = LATENCY_CYCLES


def pack_bcrc_word(crc30: int, error_flag: int = 0, reserved: int = 0) -> int:
    """{rsvd, ERROR_FLAG, CRC30[29:0]} (SPEC §2.6). TX reserved = 0."""
    return ((reserved & 1) << 31) | ((error_flag & 1) << 30) | (crc30 & CRC30_MASK)


def unpack_bcrc_word(word: int) -> tuple[int, int, int]:
    reserved = (word >> 31) & 1
    error_flag = (word >> 30) & 1
    crc30 = word & CRC30_MASK
    return crc30, error_flag, reserved


def flit_to_bytes(flit: int, n: int = FLIT_BYTES) -> list[int]:
    """Byte 0 = flit[7:0] (SPEC §3.3 bit0 = LSB)."""
    return [(flit >> (8 * i)) & 0xFF for i in range(n)]


def bytes_to_flit(data: list[int]) -> int:
    acc = 0
    for i, b in enumerate(data):
        acc |= (b & 0xFF) << (8 * i)
    return acc


def word_to_le_bytes(word: int) -> list[int]:
    return [(word >> (8 * i)) & 0xFF for i in range(BCRC_BYTES)]


def le_bytes_to_word(data: list[int]) -> int:
    acc = 0
    for i, b in enumerate(data):
        acc |= (b & 0xFF) << (8 * i)
    return acc


def _update_bit(crc: int, bit: int, poly: int) -> int:
    """One MSB-first CRC step. Remainder not inverted."""
    mix = ((crc >> 29) & 1) ^ (bit & 1)
    crc = (crc << 1) & CRC30_MASK
    if mix:
        crc ^= poly
    return crc


def _update_byte(crc: int, byte: int, poly: int) -> int:
    """One data byte, bit7 then bit6 … bit0 (SPEC §2.6)."""
    for shift in range(7, -1, -1):
        crc = _update_bit(crc, (byte >> shift) & 1, poly)
    return crc


class UbDllBcrc:
    """Streaming / block BCRC. Checker compares CRC30 only."""

    def __init__(self, cfg: UbDllBcrcConfig | None = None) -> None:
        self.cfg = cfg or UbDllBcrcConfig()
        self.reset()

    def reset(self) -> None:
        self._crc = self.cfg.init & CRC30_MASK
        self._started = False

    def _payload_bytes(self, flits: list[int]) -> list[int]:
        if not flits:
            raise ValueError("DLLDB must contain at least one flit")
        raw: list[int] = []
        for flit in flits:
            raw.extend(flit_to_bytes(flit, self.cfg.flit_bytes))
        if len(raw) < BCRC_BYTES:
            raise ValueError("DLLDB shorter than the 32-bit BCRC word")
        return raw[:-BCRC_BYTES]

    def crc30_of_bytes(self, data: list[int]) -> int:
        crc = self.cfg.init & CRC30_MASK
        for byte in data:
            crc = _update_byte(crc, byte & 0xFF, self.cfg.poly)
        return crc

    def crc30_of_flits(
        self,
        flits: list[int],
        *,
        error_flag: int = 0,
        reserved: int = 0,
    ) -> int:
        # error_flag / reserved are packed after the remainder; not in the CRC.
        del error_flag, reserved
        return self.crc30_of_bytes(self._payload_bytes(flits))

    def attach(
        self,
        flits: list[int],
        *,
        error_flag: int = 0,
        reserved: int = 0,
    ) -> list[int]:
        crc30 = self.crc30_of_flits(flits)
        word = pack_bcrc_word(crc30, error_flag, reserved)
        out = list(flits)
        last = flit_to_bytes(out[-1], self.cfg.flit_bytes)
        last[-BCRC_BYTES:] = word_to_le_bytes(word)
        out[-1] = bytes_to_flit(last)
        return out

    def extract(self, flits: list[int]) -> tuple[int, int, int]:
        last = flit_to_bytes(flits[-1], self.cfg.flit_bytes)
        return unpack_bcrc_word(le_bytes_to_word(last[-BCRC_BYTES:]))

    def check(self, flits: list[int]) -> bool:
        stored, _flag, _rsvd = self.extract(flits)
        return stored == self.crc30_of_flits(flits)

    def start(self) -> None:
        self.reset()
        self._started = True

    def eat(self, flit: int, *, last: bool = False) -> int | None:
        """Feed one 160-bit flit. On last, CRC the payload bytes of this beat
        except the trailing BCRC word. Returns CRC30 when last, else None."""
        if not self._started:
            self.start()
        raw = flit_to_bytes(flit, self.cfg.flit_bytes)
        body = raw[:-BCRC_BYTES] if last else raw
        for byte in body:
            self._crc = _update_byte(self._crc, byte, self.cfg.poly)
        if last:
            crc30 = self._crc
            self._started = False
            return crc30
        return None


UbDllBcrcCheck = UbDllBcrc
