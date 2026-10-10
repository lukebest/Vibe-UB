"""Lane distribution. UB-PHY §3.2.2.3 / §3.2.5 / §3.4.1; SPEC §3.3 LSB pack."""

from __future__ import annotations

import random

import pytest

from model.config import PendingParams
from model.ub_pcs_lane_dist import (
    LATENCY_CYCLES,
    PMA_W,
    RS_N,
    UbPcsLaneDist,
    UbPcsLaneDistConfig,
    pack_pma_word,
    unpack_pma_word,
)


def _ca(seed: int = 1) -> list[int]:
    rng = random.Random(seed)
    return [rng.randrange(256) for _ in range(RS_N)]


def test_latency_is_zero():
    assert LATENCY_CYCLES == 0
    assert UbPcsLaneDistConfig().latency_cycles == 0


@pytest.mark.parametrize("lane_num", [1, 2, 4, 8])
def test_distribute_then_recover_codec1(lane_num):
    dist = UbPcsLaneDist(lane_num)
    ca = _ca(lane_num)
    lanes = dist.distribute(ca)
    got, cb = dist.recover(lanes)
    assert cb is None
    assert got == ca
    assert len(lanes) == lane_num
    assert all(len(lane) == RS_N // lane_num for lane in lanes)


def test_codec1_x4_first_symbols_match_formula():
    # UB-PHY §3.2.2.3: Lane<j,0> = CA<(N-1)-j>
    ca = list(range(RS_N))
    lanes = UbPcsLaneDist(4).distribute(ca)
    assert lanes[0][0] == ca[127]
    assert lanes[1][0] == ca[126]
    assert lanes[2][0] == ca[125]
    assert lanes[3][0] == ca[124]
    assert lanes[0][1] == ca[123]


def test_codec1_x1_is_reversed_codeword():
    ca = list(range(RS_N))
    lanes = UbPcsLaneDist(1).distribute(ca)
    assert lanes[0] == list(reversed(ca))


@pytest.mark.parametrize("lane_num", [1, 2, 4, 8])
def test_distribute_then_recover_codec2(lane_num):
    cfg = UbPcsLaneDistConfig(pending=PendingParams(fec_codec_num=2))
    dist = UbPcsLaneDist(lane_num, cfg)
    ca, cb = _ca(10), _ca(11)
    lanes = dist.distribute(ca, cb)
    got_a, got_b = dist.recover(lanes)
    assert got_a == ca
    assert got_b == cb


def test_codec2_x1_alternates_ca_cb():
    cfg = UbPcsLaneDistConfig(pending=PendingParams(fec_codec_num=2))
    ca = list(range(RS_N))
    cb = [(x + 200) & 0xFF for x in range(RS_N)]
    lane0 = UbPcsLaneDist(1, cfg).distribute(ca, cb)[0]
    assert lane0[0] == ca[127]
    assert lane0[1] == cb[127]
    assert lane0[2] == ca[126]
    assert lane0[3] == cb[126]


def test_symbols_are_8bit():
    ca = [0x1FF] * RS_N
    lanes = UbPcsLaneDist(4).distribute(ca)
    assert all(0 <= s <= 255 for lane in lanes for s in lane)


def test_reject_bad_lane_num():
    with pytest.raises(ValueError):
        UbPcsLaneDist(3)


def test_pma_word_symbol0_at_lsb():
    # SPEC §3.3: symbol 0 is the lowest byte; bit0 is LSB.
    word = pack_pma_word([0xA1, 0xB2, 0xC3, 0xD4], PMA_W, 8)
    assert word & 0xFF == 0xA1
    assert (word >> 8) & 0xFF == 0xB2
    assert (word >> 24) & 0xFF == 0xD4
    assert unpack_pma_word(word) == [0xA1, 0xB2, 0xC3, 0xD4]


def test_pack_lane_words_roundtrip():
    dist = UbPcsLaneDist(4)
    ca = list(range(RS_N))
    lanes = dist.distribute(ca)
    words = dist.pack_lane_words(lanes)
    assert all(0 <= w < (1 << PMA_W) for lane in words for w in lane)
    restored = dist.unpack_lane_words(words)
    assert restored == lanes
    got, _ = dist.recover(restored)
    assert got == ca
