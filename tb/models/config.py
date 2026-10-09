"""Pending / draft parameters that models must not invent as closed.

Values here are *defaults for the model*, not captain-closed SPEC §9 items.
Cite the section that left the item open. See SPEC §13 and UB-PHY / UB-DL gaps.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PendingParams:
    """Open knobs collected while writing the M1 golden models."""

    # UB-PHY §3.2.2.4 does not write LFSR taps. UB-PHY §3.2.6 says the
    # low-power PRBS23 polynomial is the same as the scrambler's.
    # Default taps implement that PRBS23 (x^23 + x^18 + 1). Confirm vs the
    # official figure if one exists outside the public extract.
    scrambler_poly_taps: tuple[int, ...] = (23, 18)
    scrambler_width: int = 23

    # UB-PHY §3.2.2.4: seeds come from AMCTL lane IDs, but no seed table
    # is written in that section. Default = all-1s per lane (overridable).
    scrambler_seed_all_ones: bool = True
    scrambler_seeds_by_lane: dict[int, int] | None = None

    # Which LFSR bit is XOR'd with data, and Fibonacci vs Galois.
    # Not written in UB-PHY §3.2.2.4. Default: Fibonacci, XOR with MSB.
    scrambler_structure: str = "fibonacci"
    scrambler_out_bit: str = "msb"

    # Exempt symbols (AMCTL / EEIB) are not fed to the descrambler
    # (UB-PHY §3.2.3.2). Default: do not advance the LFSR on exempt symbols.
    scrambler_advance_on_exempt: bool = False

    # SPEC §9 / UB-PHY §3.2.2.3: FEC_CODEC_NUM is 待定 (suggest 1).
    fec_codec_num: int = 1

    # UB-DL §4.7.2: CRC30 covers "all data before the CRC30 field".
    # Default includes Reserved + ERROR_FLAG (they sit before CRC30 in
    # UB-DL §4.3.2.2.4). Flip this only if architecture closes otherwise.
    bcrc_include_info_bits: bool = True

    # How the 32-bit BCRC word is packed into the last flit bytes 16–19.
    # Default: byte 16 holds {Reserved, ERROR_FLAG, CRC30[29:24]} (MSB-first
    # field packing implied by UB-DL §4.3.2.2.4 + §4.7.2 "no reordering").
    bcrc_byte16_is_msb: bool = True

    notes: tuple[str, ...] = field(
        default_factory=lambda: (
            "scrambler polynomial taps: UB-PHY §3.2.2.4 silent; §3.2.6 PRBS23 default",
            "scrambler per-lane seeds: UB-PHY §3.2.2.4 / §3.2.4 AMCTL.LID identify the seed, table not written",
            "scrambler LFSR structure / out bit: not written in UB-PHY §3.2.2.4",
            "FEC_CODEC_NUM: SPEC §9 / §13.2 待定 (default 1)",
            "BCRC info-bit coverage: UB-DL §4.7.2 'before CRC30'; confirm vs Figure 4-39",
            "BCRC byte packing in the 160b flit: project little-endian bytes (REGMAP) + field MSB in byte 16",
        )
    )


PENDING = PendingParams()
