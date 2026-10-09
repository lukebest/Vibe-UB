"""ub_pcs_scrambler / ub_pcs_descrambler interface (CODING_STYLE §5).

Normative: UB-PHY §3.2.2.4 / §3.2.3.2 / §3.2.6. Project: SPEC §2.4, §9, §13.

Known (do not invent the rest):
- Seed source is AMCTL.LID, not the physical lane index, not LTB.Lane_ID.
- Leaf port ``amctl_lid[3:0]``: 0–7 = Lane0–7, 8 = NULL, 9–15 reserved.
- Each symbol: bit0 is LSB; LSB is scrambled first.
- EEIB / AMCTL: not scrambled (``en=0``, LFSR does not step).
- LTB and DLL payload: scrambled (``en=1``).
- One instance per physical lane; data port ``DATA_W = PMA_W = 32``; LFSR ``SCR_W = 23``.
- Valid-only; latency 1 cycle; ``valid_out=0`` after reset.

Pending SPEC §13 — core step raises ``NotImplementedError("pending SPEC")``:
PRBS23 taps, LID→seed map, NULL seed, power-on LFSR init.
Do not copy PR #5 / Switch defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from tb.models.config import PENDING, PENDING_SPEC, PendingParams


class SymbolKind(Enum):
    """What a symbol is (UB-PHY §3.2.2.4)."""

    DLL = "dll"
    LTB = "ltb"
    AMCTL = "amctl"
    EEIB = "eeib"


@dataclass
class UbPcsScramblerConfig:
    """Closed widths plus pending knobs. No poly / seed table."""

    pending: PendingParams = field(default_factory=lambda: PENDING)
    symbol_bits: int = 8
    lsb_first: bool = True
    latency_cycles: int = 1

    @property
    def data_w(self) -> int:
        return self.pending.scrambler_data_w

    @property
    def scr_w(self) -> int:
        return self.pending.scrambler_width


# Leaf ports (SPEC §2.4; PR #5 description for agent wiring only).
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

AMCTL_LID_NULL = 8
AMCTL_LID_LANE_MAX = 7


class UbPcsScrambler:
    """Per-lane additive scrambler skeleton. Same body as the descrambler."""

    def __init__(
        self,
        cfg: UbPcsScramblerConfig | None = None,
        *,
        amctl_lid: int = 0,
    ) -> None:
        self.cfg = cfg or UbPcsScramblerConfig()
        if not 0 <= amctl_lid <= 15:
            raise ValueError(f"amctl_lid out of 4-bit range: {amctl_lid}")
        self.amctl_lid = amctl_lid

    def should_scramble(self, kind: SymbolKind) -> bool:
        return kind in (SymbolKind.DLL, SymbolKind.LTB)

    def seed_source_is_amctl_lid(self) -> bool:
        """UB-PHY §3.2.2.4: seed follows AMCTL.LID, not phys / LTB.Lane_ID."""
        return True

    def process_symbol(self, symbol: int, kind: SymbolKind) -> int:
        raise NotImplementedError(PENDING_SPEC)

    def process_word(self, data: int, *, en: bool) -> int:
        raise NotImplementedError(PENDING_SPEC)

    def load_seed_from_amctl_lid(self, amctl_lid: int) -> None:
        raise NotImplementedError(PENDING_SPEC)

    def reset(self) -> None:
        raise NotImplementedError(PENDING_SPEC)


UbPcsDescrambler = UbPcsScrambler
