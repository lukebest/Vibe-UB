"""Pure-Python self-check of the bypass scoreboard (no RTL, no cocotb).

The architecture model is the oracle. These tests pass once the #64
model is present, even without the DUT.
"""

from __future__ import annotations

import inspect

import pytest

from model.tp.ub_tp_bypass import (
    CFG_BYPASS,
    UNKNOWNS,
    UbTpBypass,
    UbTpBypassError,
)
from tb.tp.handle import FakeBypassHandle
from tb.tp.items import RX_CHECKED, TX_CHECKED, UNCHECKED
from tb.tp.run_txn import run_plan
from tb.tp.scoreboard import TpBypassScoreboard
from tb.tp.sequences import (
    DIRECTED_CASES,
    expected_compares,
    make_plan,
    plan_drop_then_keep,
    plan_random,
    plan_single_tx,
)

SEED = 1


@pytest.mark.parametrize("case", DIRECTED_CASES)
def test_directed_match_model(case):
    print(f"SEED {SEED}", flush=True)
    plan = make_plan(case, seed=SEED)
    _h, sb, want = run_plan(plan)
    assert sb.n_compare > 0
    assert sb.n_compare == want
    assert sb.n_mismatch == 0
    assert sb.n_skip == 0
    print(f"n_compare {case}={sb.n_compare}", flush=True)


def test_random_matches_model():
    print(f"SEED {SEED}", flush=True)
    plan = plan_random(SEED)
    _h, sb, want = run_plan(plan)
    assert sb.n_compare == want == expected_compares(plan)
    assert sb.n_compare > 0
    assert sb.n_skip == 0
    print(f"n_compare random={sb.n_compare}", flush=True)


def test_drop_then_keep_model_only():
    """``nw2tp_drop`` is not a DUT pin; the model still discards."""
    print(f"SEED {SEED}", flush=True)
    plan = plan_drop_then_keep()
    _h, sb, want = run_plan(plan)
    assert want == 1
    assert sb.n_compare == 1
    assert sb.n_skip == 0
    print(f"n_compare drop_then_keep={sb.n_compare}", flush=True)


def test_icrc_stays_zero():
    m = UbTpBypass()
    from tb.tp.items import flits_from_data

    m.receive(flits_from_data((1,)), err=True)
    assert m.nw2tp_icrc_err == 0
    m.nw2tp_icrc_err = 1
    m.receive(flits_from_data((2,)))
    assert m.nw2tp_icrc_err == 0


def test_scoreboard_catches_data_swap():
    print(f"SEED {SEED}", flush=True)
    handle = FakeBypassHandle(swap_data=True)
    sb = TpBypassScoreboard()
    with pytest.raises(AssertionError, match="data"):
        run_plan(plan_single_tx(), handle=handle, scoreboard=sb)
    assert sb.n_mismatch >= 1
    assert sb.n_compare >= 1


def test_scoreboard_catches_dcna_alias():
    print(f"SEED {SEED}", flush=True)
    handle = FakeBypassHandle(alias_dcna=True)
    sb = TpBypassScoreboard()
    with pytest.raises(AssertionError, match="dcna"):
        run_plan(plan_single_tx(), handle=handle, scoreboard=sb)
    assert sb.n_mismatch >= 1


def test_scoreboard_catches_bypass_cleared():
    print(f"SEED {SEED}", flush=True)
    handle = FakeBypassHandle(clear_bypass=True)
    sb = TpBypassScoreboard()
    with pytest.raises(AssertionError, match="bypass"):
        run_plan(plan_single_tx(), handle=handle, scoreboard=sb)
    assert sb.n_mismatch >= 1


def test_scoreboard_catches_sl_nonzero():
    """Wave-1 leaf ties sl to 0; a non-zero output must fail vs the model."""
    print(f"SEED {SEED}", flush=True)
    handle = FakeBypassHandle(force_sl=1)
    sb = TpBypassScoreboard()
    with pytest.raises(AssertionError, match="sl"):
        run_plan(plan_single_tx(), handle=handle, scoreboard=sb)
    assert sb.n_mismatch >= 1


def test_n_compare_equals_declared():
    plan = make_plan("mixed")
    want = expected_compares(plan)
    assert want == 4
    _h, sb, got = run_plan(plan)
    assert sb.n_compare == got == want
    assert sb.n_skip == 0


def test_unknown_fields_not_checked():
    blob = " ".join(UNKNOWNS).lower()
    assert "ta2tp_op_len" in blob
    assert "ta2tp_mode" in blob
    assert "rspst" in blob and "rspinfo" in blob
    assert "24-bit dcna" in blob
    src = inspect.getsource(TpBypassScoreboard)
    for name in UNCHECKED:
        # Scoreboard may mention the name only to say it is not compared.
        if name in ("opcode", "tassn", "tpmsn", "done", "fail"):
            continue
        assert name not in TX_CHECKED
        assert name not in RX_CHECKED
    assert "ta2tp_mode" not in src
    assert "op_len" not in src
    assert "rspst" not in src
    assert "dcna24" not in src
    assert set(TX_CHECKED) == {
        "data",
        "sop",
        "eop",
        "bypass",
        "dcna",
        "sl",
        "nlp",
        "lbf",
        "rt",
        "cci",
    }
    assert set(RX_CHECKED) == {"data", "sop", "eop", "err"}
    assert CFG_BYPASS == 9


def test_flush_rejects_new_tx_on_fake():
    handle = FakeBypassHandle()
    sb = TpBypassScoreboard()
    run_plan(make_plan("single_tx"), handle=handle, scoreboard=sb)
    sb.apply_flush()
    handle.flush = True
    with pytest.raises(RuntimeError, match="blocked"):
        handle.send_tx(plan_single_tx()[0][1])
    with pytest.raises(UbTpBypassError, match="flush"):
        sb.expect_tx(plan_single_tx(tassn=99)[0][1])
