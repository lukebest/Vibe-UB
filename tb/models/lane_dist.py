"""8-bit FEC-symbol lane distribution / recovery.

Normative: UB-PHY §3.2.2.3 (post-FEC distribution), §3.2.5 (bit/symbol order).
Project: SPEC §2.4, §9 (x1/x4 bring-up, parameterize to x8). Not 2-bit slices.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tb.models.config import PENDING, PendingParams

RS_N = 128  # UB-PHY §3.2.2.1 RS(128,120): N = 128 symbols per codeword
RS_K = 120
SYMBOL_BITS = 8  # UB-PHY §3.2.5.1; SPEC §2.4


@dataclass
class LaneDistConfig:
    pending: PendingParams = field(default_factory=lambda: PENDING)
    n_symbols: int = RS_N
    symbol_bits: int = SYMBOL_BITS

    @property
    def codec_num(self) -> int:
        return self.pending.fec_codec_num


def _check_lane_num(lane_num: int) -> None:
    if lane_num not in (1, 2, 4, 8):
        raise ValueError(f"LaneNum must be 1/2/4/8 (UB-PHY §3.1.1), got {lane_num}")


class LaneDist:
    """Distribute CA (and optional CB) symbols onto lanes; invert to recover."""

    def __init__(self, lane_num: int, cfg: LaneDistConfig | None = None) -> None:
        _check_lane_num(lane_num)
        self.lane_num = lane_num
        self.cfg = cfg or LaneDistConfig()
        n = self.cfg.n_symbols
        if self.cfg.codec_num == 1 and n % lane_num != 0:
            raise ValueError(f"N={n} must be divisible by LaneNum={lane_num} (UB-PHY §3.2.2.3)")

    def distribute(
        self,
        codeword_a: list[int],
        codeword_b: list[int] | None = None,
    ) -> list[list[int]]:
        """Return lanes[j][i] = symbol i on lane j.

        Codeword index k is CA<k> / CB<k> (UB-PHY §3.2.2.3).
        """
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
        """Inverse of distribute (UB-PHY §3.2.3.3 / §3.2.3.4 pairing)."""
        if len(lanes) != self.lane_num:
            raise ValueError(f"expected {self.lane_num} lanes, got {len(lanes)}")
        codec = self.cfg.codec_num
        if codec == 1:
            return self._rec_non_interleaved(lanes), None
        if codec == 2:
            return self._rec_interleaved(lanes)
        raise ValueError(f"CodecNum {codec} not modelled")

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
        # UB-PHY §3.2.2.3 CodecNum=2
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
        # LaneNum = 2/4/8
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
