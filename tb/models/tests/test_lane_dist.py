"""Lane distribution properties. UB-PHY §3.2.2.3 / §3.2.5. Formula is the known vector."""

from __future__ import annotations

import random

import pytest

from tb.models.config import PendingParams
from tb.models.lane_dist import RS_N, LaneDist, LaneDistConfig


def _ca(seed: int = 1) -> list[int]:
    rng = random.Random(seed)
    return [rng.randrange(256) for _ in range(RS_N)]


@pytest.mark.parametrize("lane_num", [1, 2, 4, 8])
def test_distribute_then_recover_codec1(lane_num):
    dist = LaneDist(lane_num)
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
    lanes = LaneDist(4).distribute(ca)
    assert lanes[0][0] == ca[127]
    assert lanes[1][0] == ca[126]
    assert lanes[2][0] == ca[125]
    assert lanes[3][0] == ca[124]
    assert lanes[0][1] == ca[123]


def test_codec1_x1_is_reversed_codeword():
    ca = list(range(RS_N))
    lanes = LaneDist(1).distribute(ca)
    assert lanes[0] == list(reversed(ca))


@pytest.mark.parametrize("lane_num", [1, 2, 4, 8])
def test_distribute_then_recover_codec2(lane_num):
    cfg = LaneDistConfig(pending=PendingParams(fec_codec_num=2))
    dist = LaneDist(lane_num, cfg)
    ca, cb = _ca(10), _ca(11)
    lanes = dist.distribute(ca, cb)
    got_a, got_b = dist.recover(lanes)
    assert got_a == ca
    assert got_b == cb


def test_codec2_x1_alternates_ca_cb():
    cfg = LaneDistConfig(pending=PendingParams(fec_codec_num=2))
    ca = list(range(RS_N))
    cb = [(x + 200) & 0xFF for x in range(RS_N)]
    lane0 = LaneDist(1, cfg).distribute(ca, cb)[0]
    assert lane0[0] == ca[127]
    assert lane0[1] == cb[127]
    assert lane0[2] == ca[126]
    assert lane0[3] == cb[126]


def test_symbols_are_8bit():
    ca = [0x1FF] * RS_N  # truncated to 8 bits
    lanes = LaneDist(4).distribute(ca)
    assert all(0 <= s <= 255 for lane in lanes for s in lane)


def test_reject_bad_lane_num():
    with pytest.raises(ValueError):
        LaneDist(3)
