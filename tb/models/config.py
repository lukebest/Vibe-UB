"""Pending knobs that goldens must not invent.

BCRC is closed in SPEC §2.6. Scrambler taps and AMCTL.LID → seed stay
SPEC §13: required arguments on UbPcsScramblerConfig, no defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PendingParams:
    fec_codec_num: int = 1

    notes: tuple[str, ...] = field(
        default_factory=lambda: (
            "scrambler poly_taps and lid_to_seed: SPEC §13 — required, no default",
            "FEC_CODEC_NUM: SPEC §9 / §13.2 待定 (default 1 for lane-dist formula)",
        )
    )


PENDING = PendingParams()
