"""GATE-TB-SB-001: compare count > 0 and equals expected. 0 skip."""

from __future__ import annotations

import pytest

from tb.contracts.scoreboard import ContractScoreboard


def test_compare_count_must_be_positive():
    sb = ContractScoreboard("empty", {"tx": 0, "rx": 0, "total": 1})
    with pytest.raises(AssertionError, match="n_compare=0"):
        sb.check()


def test_compare_count_must_match_expected():
    sb = ContractScoreboard("short", {"tx": 2, "rx": 0, "total": 2})
    sb.compare("tx", 1, 1, "a")
    with pytest.raises(AssertionError, match="n_compare=1 != expected 2"):
        sb.check()


def test_side_count_must_match():
    sb = ContractScoreboard("sides", {"tx": 1, "rx": 1, "total": 2})
    sb.compare("tx", 1, 1)
    sb.compare("tx", 2, 2)
    with pytest.raises(AssertionError, match="side tx"):
        sb.check()


def test_mismatch_fails():
    sb = ContractScoreboard("mm", {"tx": 1, "rx": 0, "total": 1})
    assert sb.compare("tx", 1, 2, "x") is False
    with pytest.raises(AssertionError, match="1 mismatch"):
        sb.check()


def test_paired_sides_pass_when_counts_match():
    sb = ContractScoreboard("ok", {"tx": 2, "rx": 2, "total": 4})
    assert sb.compare("tx", {"a": 1}, {"a": 1})
    assert sb.compare("tx", {"a": 2}, {"a": 2})
    assert sb.compare("rx", {"b": 3}, {"b": 3})
    assert sb.compare("rx", {"b": 4}, {"b": 4})
    sb.check()
    assert sb.n_compare == 4
    assert sb.n_mismatch == 0
