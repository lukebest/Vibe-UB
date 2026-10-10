"""ub_pcs_lane_dist / ub_pcs_lane_dedist (CODING_STYLE §5).

Normative: UB-PHY §3.2.2.3 (post-FEC distribution), §3.2.5, §3.4.1.
Project: SPEC §2.4, §3.3, §9. 8-bit FEC symbols, not 2-bit slices.

Closed project conventions:
- Symbol 0 is sent first (UB-PHY §3.4.1).
- Inside a PMA word, symbol 0 sits at the LSB byte (SPEC §3.3).
- Multi-lane pack: lane 0 at the bus LSB (SPEC §3.2.4).
- Latency 0 cycles (combinational).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tb.models.config import PENDING, PendingParams

RS_N = 128
RS_K = 120
SYMBOL_BITS = 8
PMA_W = 32
LATENCY_CYCLES = 0

LEAF_PORTS = ("data_in", "data_out")


@dataclass
class UbPcsLaneDistConfig:
    pending: PendingParams = field(default_factory=lambda: PENDING)
    n_symbols: int = RS_N
    symbol_bits: int = SYMBOL_BITS
    pma_w: int = PMA_W
    latency_cycles: int = LATENCY_CYCLES

    @property
    def codec_num(self) -> int:
        return self.pending.fec_codec_num

    @property
    def symbols_per_pma_word(self) -> int:
        if self.pma_w % self.symbol_bits != 0:
            raise ValueError(f"PMA_W={self.pma_w} must be a multiple of {self.symbol_bits}")
        return self.pma_w // self.symbol_bits


def _check_lane_num(lane_num: int) -> None:
    if lane_num not in (1, 2, 4, 8):
        raise ValueError(f"LaneNum must be 1/2/4/8 (UB-PHY §3.1.1), got {lane_num}")


def pack_pma_word(symbols: list[int], pma_w: int = PMA_W, symbol_bits: int = SYMBOL_BITS) -> int:
    """Pack symbol-major bytes into one PMA word. Symbol 0 at the LSB (SPEC §3.3)."""
    n = pma_w // symbol_bits
    if len(symbols) != n:
        raise ValueError(f"need {n} symbols for PMA_W={pma_w}, got {len(symbols)}")
    word = 0
    for i, sym in enumerate(symbols):
        word |= (sym & 0xFF) << (i * symbol_bits)
    return word


def unpack_pma_word(word: int, pma_w: int = PMA_W, symbol_bits: int = SYMBOL_BITS) -> list[int]:
    """Inverse of pack_pma_word. Symbol 0 is the LSB byte."""
    n = pma_w // symbol_bits
    mask = (1 << symbol_bits) - 1
    return [(word >> (i * symbol_bits)) & mask for i in range(n)]


class UbPcsLaneDist:
    """Distribute CA (and optional CB) symbols onto lanes; invert to recover."""

    def __init__(self, lane_num: int, cfg: UbPcsLaneDistConfig | None = None) -> None:
        _check_lane_num(lane_num)
        self.lane_num = lane_num
        self.cfg = cfg or UbPcsLaneDistConfig()
        n = self.cfg.n_symbols
        if self.cfg.codec_num == 1 and n % lane_num != 0:
            raise ValueError(f"N={n} must be divisible by LaneNum={lane_num} (UB-PHY §3.2.2.3)")

    def distribute(
        self,
        codeword_a: list[int],
        codeword_b: list[int] | None = None,
    ) -> list[list[int]]:
        """Return lanes[j][i] = symbol i on lane j. Symbol 0 is first on the wire."""
        n = self.cfg.n_symbols
        if len(codeword_a) != n:
            raise ValueError(f"CA must have {n} symbols, got {len(codeword_a)}")
        ca = [s & 0xFF for s in codeword_a]
        codec = self.cfg.codec_num
        if codec == 1:
            return self._dist_non_interleaved(ca)
        if codec == 2:
            if codeword_b is None or len(codeword_b) != n:
                raise ValueError("CodecNum=2 needs CB of N symbols (UB-PHY §3.2.2.3)")
            cb = [s & 0xFF for s in codeword_b]
            return self._dist_interleaved(ca, cb)
        raise ValueError(f"CodecNum {codec} not modelled")

    def recover(self, lanes: list[list[int]]) -> tuple[list[int], list[int] | None]:
        if len(lanes) != self.lane_num:
            raise ValueError(f"expected {self.lane_num} lanes, got {len(lanes)}")
        codec = self.cfg.codec_num
        if codec == 1:
            return self._rec_non_interleaved(lanes), None
        if codec == 2:
            return self._rec_interleaved(lanes)
        raise ValueError(f"CodecNum {codec} not modelled")

    def pack_lane_words(self, lanes: list[list[int]]) -> list[list[int]]:
        """Group each lane's symbols into PMA words, symbol 0 at LSB. 0-cycle."""
        n = self.cfg.symbols_per_pma_word
        packed: list[list[int]] = []
        for lane in lanes:
            if len(lane) % n != 0:
                raise ValueError(f"lane length {len(lane)} not a multiple of {n}")
            words = [pack_pma_word(lane[i : i + n], self.cfg.pma_w, self.cfg.symbol_bits)
                     for i in range(0, len(lane), n)]
            packed.append(words)
        return packed

    def unpack_lane_words(self, words: list[list[int]]) -> list[list[int]]:
        return [
            [s for word in lane_words
             for s in unpack_pma_word(word, self.cfg.pma_w, self.cfg.symbol_bits)]
            for lane_words in words
        ]

    def _dist_non_interleaved(self, ca: list[int]) -> list[list[int]]:
        # UB-PHY §3.2.2.3 CodecNum=1:
        #   for i=0 to (N/LaneNum-1)
        #     for j=0 to (LaneNum-1)
        #       Lane<j,i> = CA<(N-1)-i*LaneNum-j>
        n = self.cfg.n_symbols
        ln = self.lane_num
        lanes = [[] for _ in range(ln)]
        for i in range(n // ln):
            for j in range(ln):
                lanes[j].append(ca[(n - 1) - i * ln - j])
        return lanes

    def _rec_non_interleaved(self, lanes: list[list[int]]) -> list[int]:
        n = self.cfg.n_symbols
        ln = self.lane_num
        ca = [0] * n
        for i in range(n // ln):
            for j in range(ln):
                ca[(n - 1) - i * ln - j] = lanes[j][i] & 0xFF
        return ca

    def _dist_interleaved(self, ca: list[int], cb: list[int]) -> list[list[int]]:
        n = self.cfg.n_symbols
        ln = self.lane_num
        lanes = [[] for _ in range(ln)]
        if ln == 1:
            for i in range(n * 2):
                if i % 2 == 0:
                    lanes[0].append(ca[(n - 1) - i // 2])
                else:
                    lanes[0].append(cb[(n - 1) - (i - 1) // 2])
            return lanes
        for i in range(n * 2 // ln):
            for j in range(ln // 2):
                if i % 2 == 0:
                    lanes[j * 2].append(ca[(n - 1) - i * (ln // 2) - j])
                    lanes[j * 2 + 1].append(cb[(n - 1) - i * (ln // 2) - j])
                else:
                    lanes[j * 2].append(cb[(n - 1) - i * (ln // 2) - j])
                    lanes[j * 2 + 1].append(ca[(n - 1) - i * (ln // 2) - j])
        return lanes

    def _rec_interleaved(self, lanes: list[list[int]]) -> tuple[list[int], list[int]]:
        n = self.cfg.n_symbols
        ln = self.lane_num
        ca = [0] * n
        cb = [0] * n
        if ln == 1:
            for i in range(n * 2):
                if i % 2 == 0:
                    ca[(n - 1) - i // 2] = lanes[0][i] & 0xFF
                else:
                    cb[(n - 1) - (i - 1) // 2] = lanes[0][i] & 0xFF
            return ca, cb
        for i in range(n * 2 // ln):
            for j in range(ln // 2):
                if i % 2 == 0:
                    ca[(n - 1) - i * (ln // 2) - j] = lanes[j * 2][i] & 0xFF
                    cb[(n - 1) - i * (ln // 2) - j] = lanes[j * 2 + 1][i] & 0xFF
                else:
                    cb[(n - 1) - i * (ln // 2) - j] = lanes[j * 2][i] & 0xFF
                    ca[(n - 1) - i * (ln // 2) - j] = lanes[j * 2 + 1][i] & 0xFF
        return ca, cb


UbPcsLaneDedist = UbPcsLaneDist
