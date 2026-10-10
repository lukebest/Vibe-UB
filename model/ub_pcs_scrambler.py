"""ub_pcs_scrambler / ub_pcs_descrambler (CODING_STYLE §5).

SPEC §2.4 (UB-PHY §3.2.2.4 / §3.2.3.2 / §3.2.6):

- Additive PRBS23 per physical lane; TX and RX use the same body.
- ``SCR_W=23``, datapath ``DATA_W=PMA_W=32``; ``data[0]`` is the first
  LSB-first bit of the beat.
- Seed *source* is ``AMCTL.LID``, not the physical index, not LTB.Lane_ID.
- LSB of each scrambled symbol first; EEIB/AMCTL bypass (LFSR does not step);
  LTB and DLL payload are scrambled.
- Seed reload: LMSM not in Send_NullBlock / Link_Active, AMCTL with EDF →
  reload from the LID map. LMSM in those two states, AMCTL with SDF → do not
  reload.

SPEC §13 still open — required constructor parameters, **no defaults**:

- ``poly_taps``: 1-indexed degrees of g(x), including 23. Do not invent a
  project default; tests pass an explicit 示例 tuple.
- ``lid_to_seed``: ``AMCTL.LID`` → 23-bit seed. Same rule.

Fibonacci LFSR: output = MSB; feedback = XOR of tap bits; shift left, new
LSB = feedback. Additive XOR is self-inverse.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum

SCR_W = 23
DATA_W = 32
LATENCY_CYCLES = 1
AMCTL_LID_NULL = 8
AMCTL_LID_LANE_MAX = 7

LEAF_PORTS = (
    "core_clk",
    "rst_pyc",
    "amctl_lid",
    "seed_load",
    "en",
    "valid_in",
    "data_in",
    "valid_out",
    "data_out",
)


class SymbolKind(Enum):
    DLL = "dll"
    LTB = "ltb"
    AMCTL = "amctl"
    EEIB = "eeib"


def _mask(width: int) -> int:
    return (1 << width) - 1


@dataclass(frozen=True)
class UbPcsScramblerConfig:
    """Closed widths plus required §13 knobs. ``poly_taps`` / ``lid_to_seed``
    have no defaults."""

    poly_taps: tuple[int, ...]
    lid_to_seed: Callable[[int], int] | Mapping[int, int]
    scr_w: int = SCR_W
    data_w: int = DATA_W
    lsb_first: bool = True
    latency_cycles: int = LATENCY_CYCLES

    def __post_init__(self) -> None:
        if not self.poly_taps:
            raise ValueError("poly_taps is required (SPEC §13, no default)")
        if self.lid_to_seed is None:
            raise ValueError("lid_to_seed is required (SPEC §13, no default)")
        if max(self.poly_taps) != self.scr_w or min(self.poly_taps) < 1:
            raise ValueError(
                f"poly_taps {self.poly_taps} must be 1-indexed degrees up to scr_w={self.scr_w}"
            )


class _FibLfsr:
    def __init__(self, width: int, taps: tuple[int, ...], seed: int) -> None:
        self.width = width
        self.taps = taps
        self.mask = _mask(width)
        self.state = seed & self.mask

    def advance(self) -> int:
        out = (self.state >> (self.width - 1)) & 1
        fb = 0
        for tap in self.taps:
            fb ^= (self.state >> (tap - 1)) & 1
        self.state = ((self.state << 1) | fb) & self.mask
        return out

    def load(self, seed: int) -> None:
        self.state = seed & self.mask


class UbPcsScrambler:
    """One additive PRBS23 per physical lane instance."""

    def __init__(self, cfg: UbPcsScramblerConfig, *, amctl_lid: int = 0) -> None:
        if not 0 <= amctl_lid <= 15:
            raise ValueError(f"amctl_lid out of 4-bit range: {amctl_lid}")
        self.cfg = cfg
        self.amctl_lid = amctl_lid
        self._lfsr = _FibLfsr(cfg.scr_w, cfg.poly_taps, self.seed_of(amctl_lid))

    def seed_of(self, amctl_lid: int) -> int:
        mapping = self.cfg.lid_to_seed
        if callable(mapping):
            return int(mapping(amctl_lid)) & _mask(self.cfg.scr_w)
        if amctl_lid not in mapping:
            raise KeyError(f"lid_to_seed has no entry for AMCTL.LID={amctl_lid}")
        return int(mapping[amctl_lid]) & _mask(self.cfg.scr_w)

    def seed_source_is_amctl_lid(self) -> bool:
        return True

    def should_scramble(self, kind: SymbolKind) -> bool:
        return kind in (SymbolKind.DLL, SymbolKind.LTB)

    def load_seed_from_amctl_lid(self, amctl_lid: int) -> None:
        if not 0 <= amctl_lid <= 15:
            raise ValueError(f"amctl_lid out of 4-bit range: {amctl_lid}")
        self.amctl_lid = amctl_lid
        self._lfsr.load(self.seed_of(amctl_lid))

    def reset(self) -> None:
        """Reload the seed for the current AMCTL.LID (seed_load)."""
        self._lfsr.load(self.seed_of(self.amctl_lid))

    def maybe_reload_seed(
        self,
        *,
        has_edf: bool,
        has_sdf: bool,
        lmsm_in_null_or_active: bool,
    ) -> None:
        """SPEC §2.4 seed-reset rules."""
        if has_edf and not lmsm_in_null_or_active:
            self.reset()
            return
        if has_sdf and lmsm_in_null_or_active:
            return

    def process_symbol(self, symbol: int, kind: SymbolKind) -> int:
        symbol &= 0xFF
        if not self.should_scramble(kind):
            return symbol
        return self._xor_bits(symbol, 8)

    def process_word(self, data: int, *, en: bool) -> int:
        data &= _mask(self.cfg.data_w)
        if not en:
            return data
        return self._xor_bits(data, self.cfg.data_w)

    def _xor_bits(self, value: int, width: int) -> int:
        out = 0
        bit_range = range(width) if self.cfg.lsb_first else range(width - 1, -1, -1)
        for i in bit_range:
            bit = (value >> i) & 1
            bit ^= self._lfsr.advance()
            out |= bit << i
        return out


UbPcsDescrambler = UbPcsScrambler
