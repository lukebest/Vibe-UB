"""ub_dll_bcrc / ub_dll_bcrc_check interface (CODING_STYLE §5).

Normative: UB-DL §4.3.2.2.4 / §4.7.2. Project: SPEC §2.6, §7.

Known packing (SPEC §2.6) — allowed on the interface:
32-bit word = {bit31 reserved=0, bit30 ERROR_FLAG, crc[29:0]}.

PR #4 ``fb330ae`` also writes poly / init / no-invert / per-byte MSB-first.
The compute body still raises ``NotImplementedError("pending SPEC")`` so
this PR does not copy PR #5 / Switch step logic. Fill in after SPEC is
treated as closed for the golden.

Valid-only streaming leaf (PR #5 ports, for agents only):
``start``, ``valid_in``, ``data_in`` (FLIT_W=160), ``last``, ``error_flag``,
``crc_word``, ``done``; check adds ``crc_recv`` / ``crc_ok``. Latency 1 cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tb.models.config import PENDING, PENDING_SPEC, PendingParams

CRC30_MASK = 0x3FFFFFFF
FLIT_W = 160
FLIT_BYTES = 20
BCRC_BYTES = 4
WORD_W = 32
LATENCY_CYCLES = 1

# Documented from SPEC §2.6 / §9. Not used by a working step in this PR.
SPEC_BCRC_POLY = 0x15A94AD5
SPEC_BCRC_INIT = 0x3FFFFFFF

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
    flit_w: int = FLIT_W
    word_w: int = WORD_W
    latency_cycles: int = LATENCY_CYCLES


def pack_bcrc_word(crc30: int, error_flag: int = 0, reserved: int = 0) -> int:
    """SPEC §2.6: {rsvd, ERROR_FLAG, CRC30[29:0]}."""
    return ((reserved & 1) << 31) | ((error_flag & 1) << 30) | (crc30 & CRC30_MASK)


def unpack_bcrc_word(word: int) -> tuple[int, int, int]:
    reserved = (word >> 31) & 1
    error_flag = (word >> 30) & 1
    crc30 = word & CRC30_MASK
    return crc30, error_flag, reserved


class UbDllBcrc:
    """BCRC generate / check skeleton. Checker compares CRC30 only (SPEC §2.6)."""

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
