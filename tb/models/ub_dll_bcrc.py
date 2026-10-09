"""ub_dll_bcrc / ub_dll_bcrc_check interface (CODING_STYLE §5).

Normative: UB-DL §4.3.2.2.4 / §4.7.2. Project: SPEC §2.6.

Known packing (allowed on the interface):
32-bit word = {bit31 reserved=0, bit30 ERROR_FLAG, crc[29:0]}
(CRC30 plus 2 info bits).

Pending SPEC — compute raises ``NotImplementedError("pending SPEC")``:
polynomial, init, invert, bit-order of the CRC step.
Do not copy PR #5 / Switch defaults.

Leaf ports / latency (PR #5 description, wiring only): valid-only,
1-cycle to ``crc_word`` / ``done``, ``valid_out``-style outputs 0 after
reset. No ready.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tb.models.config import PENDING, PENDING_SPEC, PendingParams

CRC30_MASK = 0x3FFFFFFF
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
    pending: PendingParams = field(default_factory=lambda: PENDING)
    word_w: int = WORD_W
    latency_cycles: int = LATENCY_CYCLES


def pack_bcrc_word(crc30: int, error_flag: int = 0, reserved: int = 0) -> int:
    """{rsvd, ERROR_FLAG, CRC30[29:0]} (UB-DL §4.3.2.2.4)."""
    return ((reserved & 1) << 31) | ((error_flag & 1) << 30) | (crc30 & CRC30_MASK)


def unpack_bcrc_word(word: int) -> tuple[int, int, int]:
    reserved = (word >> 31) & 1
    error_flag = (word >> 30) & 1
    crc30 = word & CRC30_MASK
    return crc30, error_flag, reserved


class UbDllBcrc:
    """BCRC generate / check skeleton."""

    def __init__(self, cfg: UbDllBcrcConfig | None = None) -> None:
        self.cfg = cfg or UbDllBcrcConfig()

    def crc30_of_flits(
        self,
        flits: list[int],
        *,
        error_flag: int = 0,
        reserved: int = 0,
    ) -> int:
        raise NotImplementedError(PENDING_SPEC)

    def attach(
        self,
        flits: list[int],
        *,
        error_flag: int = 0,
        reserved: int = 0,
    ) -> list[int]:
        raise NotImplementedError(PENDING_SPEC)

    def check(self, flits: list[int]) -> bool:
        raise NotImplementedError(PENDING_SPEC)

    def extract(self, flits: list[int]) -> tuple[int, int, int]:
        raise NotImplementedError(PENDING_SPEC)


UbDllBcrcCheck = UbDllBcrc
