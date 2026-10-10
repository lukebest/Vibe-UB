"""Checker bootstrap: SPEC formula, tb/models, and the forward map must not collapse."""

from __future__ import annotations

import pytest

from tb.vibe_uvm.bcrc_util import crc30_of, crc30_spec, payload_flit
from tb.vibe_uvm.lane_util import (
    compare_word,
    expected_window,
    first_mismatch,
    forward_dist_word,
    incrementing_symbols,
    mismatch_msg,
    spec_dist_word,
)


@pytest.mark.parametrize("num_lanes", [1, 2, 4, 8])
def test_spec_matches_model_and_rejects_forward(num_lanes):
    symbols = incrementing_symbols(num_lanes)
    spec = spec_dist_word(symbols, num_lanes)
    model = expected_window(symbols, num_lanes)
    fwd = forward_dist_word(symbols, num_lanes)
    assert spec == model
    assert spec != fwd
    hit = first_mismatch(fwd, spec, num_lanes)
    assert hit is not None
    assert hit["lane"] == 0
    # Incrementing CA[0]=0: SPEC puts it on the last stripe slot, forward on lane0 bit0.
    assert hit["bit"] == 0
    assert hit["got_bit"] == 0 or hit["exp_bit"] == 0


def test_forward_standin_fail_summary_x4():
    """What the checker reports when DUT implements Lane<j,i>=CA<i*N+j>."""
    n = 4
    symbols = incrementing_symbols(n)
    exp = spec_dist_word(symbols, n)
    got = forward_dist_word(symbols, n)
    with pytest.raises(AssertionError) as ei:
        compare_word(got, exp, n, "inc_symbols")
    msg = str(ei.value)
    assert "lane=0" in msg
    assert "bit=0" in msg
    assert mismatch_msg(got, exp, n, "inc_symbols") == msg


def test_bcrc_spec_matches_model():
    flits = [payload_flit(list(range(16)))]
    assert crc30_spec(flits) == crc30_of(flits)
