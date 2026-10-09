"""Per-lane additive scrambler / descrambler.

Normative: UB-PHY §3.2.2.4 (TX rules), §3.2.3.2 (RX), §3.2.6 (PRBS23 same poly).
Project: SPEC §2.4, §9. Do not use the legacy 58-bit / 160b-wide RTL assumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from tb.models.config import PENDING, PendingParams


class SymbolKind(Enum):
    """What a symbol is, for the exempt-vs-scramble rules (UB-PHY §3.2.2.4)."""

    DLL = "dll"  # data-link payload — scramble
    LTB = "ltb"  # link training block — scramble
    AMCTL = "amctl"  # not scrambled
    EEIB = "eeib"  # not scrambled


def _mask(width: int) -> int:
    return (1 << width) - 1


@dataclass
class ScramblerConfig:
    """Knobs. Closed rules stay hard-coded; open ones come from PendingParams."""

    pending: PendingParams = field(default_factory=lambda: PENDING)
    symbol_bits: int = 8  # UB-PHY §3.2.5.1 / SPEC: 8-bit FEC symbol
    lsb_first: bool = True  # UB-PHY §3.2.2.4: LSB first, MSB last

    @property
    def width(self) -> int:
        return self.pending.scrambler_width

    @property
    def taps(self) -> tuple[int, ...]:
        return self.pending.scrambler_poly_taps


class AdditiveLfsr:
    """Additive LFSR. Default Fibonacci, XOR data with the MSB.

    Polynomial default is PRBS23 x^23 + x^18 + 1 (UB-PHY §3.2.6).
    Structure is a pending knob (UB-PHY §3.2.2.4 does not draw the LFSR).
    """

    def __init__(self, cfg: ScramblerConfig, seed: int) -> None:
        self.cfg = cfg
        self.width = cfg.width
        if cfg.pending.scrambler_structure != "fibonacci":
            raise ValueError(
                f"only fibonacci LFSR is implemented; got {cfg.pending.scrambler_structure}"
            )
        self.state = seed & _mask(self.width)
        if self.state == 0:
            # All-zero lockup; keep a legal non-zero default (pending seed table).
            self.state = _mask(self.width)

    def peek(self) -> int:
        if self.cfg.pending.scrambler_out_bit == "msb":
            return (self.state >> (self.width - 1)) & 1
        if self.cfg.pending.scrambler_out_bit == "lsb":
            return self.state & 1
        raise ValueError(self.cfg.pending.scrambler_out_bit)

    def advance(self) -> int:
        out = self.peek()
        fb = 0
        for tap in self.cfg.taps:
            fb ^= (self.state >> (tap - 1)) & 1
        self.state = ((self.state << 1) | fb) & _mask(self.width)
        return out

    def reset(self, seed: int) -> None:
        self.state = seed & _mask(self.width)
        if self.state == 0:
            self.state = _mask(self.width)


def default_seed_for_lane(lane_id: int, cfg: ScramblerConfig) -> int:
    """Seed for one lane. Table is not in UB-PHY §3.2.2.4 — pending."""
    table = cfg.pending.scrambler_seeds_by_lane
    if table is not None and lane_id in table:
        return table[lane_id] & _mask(cfg.width)
    if cfg.pending.scrambler_seed_all_ones:
        return _mask(cfg.width)
    # Distinct non-zero placeholder so x1/x4/x8 stay distinguishable in tests.
    return ((0x5A5A5A5A ^ (lane_id * 0x9E3779B1)) | 1) & _mask(cfg.width)


class LaneScrambler:
    """One additive LFSR per lane (UB-PHY §3.2.2.4 'per-lane')."""

    def __init__(
        self,
        num_lanes: int,
        cfg: ScramblerConfig | None = None,
        seeds: dict[int, int] | None = None,
    ) -> None:
        if num_lanes not in (1, 2, 4, 8):
            raise ValueError(f"LaneNum must be 1/2/4/8 (UB-PHY §3.1.1), got {num_lanes}")
        self.cfg = cfg or ScramblerConfig()
        self.num_lanes = num_lanes
        self._seeds = {
            lane: (seeds[lane] if seeds and lane in seeds else default_seed_for_lane(lane, self.cfg))
            for lane in range(num_lanes)
        }
        self._lfsr = {
            lane: AdditiveLfsr(self.cfg, self._seeds[lane]) for lane in range(num_lanes)
        }

    def reset_lane(self, lane_id: int) -> None:
        """Reload that lane's seed (AMCTL-with-EDF case, UB-PHY §3.2.2.4)."""
        self._lfsr[lane_id].reset(self._seeds[lane_id])

    def reset_all(self) -> None:
        for lane in self._lfsr:
            self.reset_lane(lane)

    def should_scramble(self, kind: SymbolKind) -> bool:
        return kind in (SymbolKind.DLL, SymbolKind.LTB)

    def process_symbol(self, lane_id: int, symbol: int, kind: SymbolKind) -> int:
        """Scramble or pass through one 8-bit symbol. Self-inverse (additive)."""
        if not 0 <= lane_id < self.num_lanes:
            raise IndexError(lane_id)
        symbol &= 0xFF
        scramble = self.should_scramble(kind)
        lfsr = self._lfsr[lane_id]
        if not scramble:
            if self.cfg.pending.scrambler_advance_on_exempt:
                for _ in range(self.cfg.symbol_bits):
                    lfsr.advance()
            return symbol
        out = 0
        bit_range = range(self.cfg.symbol_bits)  # LSB first
        if not self.cfg.lsb_first:
            bit_range = range(self.cfg.symbol_bits - 1, -1, -1)
        for i in bit_range:
            bit = (symbol >> i) & 1
            bit ^= lfsr.advance()
            out |= bit << i
        return out

    def process_symbols(
        self, lane_id: int, symbols: list[int], kind: SymbolKind
    ) -> list[int]:
        return [self.process_symbol(lane_id, s, kind) for s in symbols]

    def maybe_reset_on_amctl(
        self,
        lane_id: int,
        *,
        has_edf: bool,
        has_sdf: bool,
        lmsm_in_null_or_active: bool,
    ) -> None:
        """UB-PHY §3.2.2.4 seed-reset rules. SDF in NULL/ACTIVE does not reset."""
        if has_edf and not lmsm_in_null_or_active:
            self.reset_lane(lane_id)
            return
        if has_sdf and lmsm_in_null_or_active:
            return
