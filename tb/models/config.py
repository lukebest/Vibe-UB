"""Pending / closed knobs for golden-model interfaces.

Closed facts come from SPEC after PR #4 `fb330ae`. Do not invent
polynomials, seeds, invert, bit-order, or DATA_W from PR #5 / Switch.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PendingParams:
    """Open knobs. Values here are not captain-closed unless SPEC says so."""

    # SPEC §2.4 / §9: DATA_W = PMA_W = 32; SCR_W = 23. Taps and
    # AMCTL.LID → seed map remain 待定 (SPEC §13).
    scrambler_data_w: int = 32
    scrambler_width: int = 23

    # SPEC §9 / UB-PHY §3.2.2.3: FEC_CODEC_NUM is 待定 (suggest 1).
    fec_codec_num: int = 1

    notes: tuple[str, ...] = field(
        default_factory=lambda: (
            "scrambler poly taps: SPEC §13 / UB-PHY §3.2.6 still 待定 — do not invent",
            "AMCTL.LID → 23-bit seed map, NULL seed, power-on LFSR: SPEC §13 待定",
            "BCRC compute body waits for the same SPEC close as the leaf; packing is known",
            "FEC_CODEC_NUM: SPEC §9 / §13.2 待定 (default 1 for lane-dist formula)",
        )
    )


PENDING = PendingParams()
PENDING_SPEC = "pending SPEC"
