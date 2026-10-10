"""Scoreboard tally: actual compares must be >0 and equal the planned count."""

from __future__ import annotations

import pytest

from tb.vibe_uvm.scoreboard import scoreboard_tally


def test_tally_ok_when_compare_matches_expect():
    assert scoreboard_tally(3, 3, 0) is None


def test_tally_rejects_zero_compares():
    assert scoreboard_tally(0, 0, 0) == "scoreboard compare count is 0"
    assert scoreboard_tally(0, 4, 0) == "scoreboard compare count is 0"


def test_tally_rejects_count_mismatch():
    assert scoreboard_tally(2, 5, 0) == "compares=2 expected=5"
    assert scoreboard_tally(5, 2, 0) == "compares=5 expected=2"


def test_tally_rejects_mismatches_after_count_ok():
    assert scoreboard_tally(4, 4, 1) == "1 scoreboard mismatches"


def test_tally_zero_wins_over_expect_mismatch():
    # A TB that never called compare() must fail even if n_expect was left 0.
    assert scoreboard_tally(0, 0, 1) == "scoreboard compare count is 0"
