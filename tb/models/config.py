"""Pending knobs for golden-model interfaces.

Do not invent polynomials, init, invert, bit-order, or scrambler DATA_W
from PR #5 / Switch. Those wait for SPEC. Known constraints live on the
model interfaces (AMCTL.LID seed source, BCRC 32-bit pack, LSB-first).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PendingParams:
    """Open knobs. No poly / init / DATA_W defaults."""

    # SPEC §9 / UB-PHY §3.2.2.3: FEC_CODEC_NUM is 待定 (suggest 1).
    # Used only by the implemented lane-dist formula.
    fec_codec_num: int = 1

    notes: tuple[str, ...] = field(
        default_factory=lambda: (
            "scrambler poly / init / invert / DATA_W: pending SPEC — do not invent",
            "AMCTL.LID → seed map: pending SPEC (seed *source* is AMCTL.LID)",
            "BCRC step (poly/init/invert/bit-order): pending SPEC; packing is known",
            "FEC_CODEC_NUM: SPEC §9 / §13.2 待定 (default 1 for lane-dist formula)",
        )
    )


PENDING = PendingParams()
PENDING_SPEC = "pending SPEC"
