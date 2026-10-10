"""cocotb + Verilator against discovered fixed netlists (SPEC §2.2).

Skipped with an explicit reason when ``rtl/cmn/`` (PRODUCT) or
``rtl/cmn/hooks/`` (TEST_HOOKS) has no parseable variants, or when
Verilator / cocotb is missing. Equivalence of the two netlists is a
gate Yosys-equiv job — this file does not run eqy.
"""

from __future__ import annotations

import pytest

from tb.cmn.discover import discover_by_netlist, rtl_sim_skip_reason
from tb.cmn.sequences import NEGATIVE_CASES, POSITIVE_CASES

SEED = 1


def _require_sim(netlist: str):
    reason = rtl_sim_skip_reason(netlist=netlist)
    if reason:
        pytest.skip(reason)
    variants = discover_by_netlist(netlist)
    if not variants:
        pytest.skip(
            f"No {netlist} ub_cmn_mem_1r1w variants under rtl/cmn/ "
            "(SPEC §2.2). design-B has not landed the leaf."
        )
    ready = []
    for var in variants:
        if "wmask" in var.ports:
            print(
                f"SKIP {var.module}: has wmask; WMASK_W segmented-write "
                "model has not landed — not this TB round",
                flush=True,
            )
            continue
        ready.append(var)
    if not ready:
        pytest.skip(
            "All discovered variants have wmask; waiting for the "
            "segmented-write model before this TB drives them."
        )
    return ready


def _is_pow2(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def _negative_cases_for(variant) -> list[str]:
    """OOR encodings do not exist when DEPTH is a power of two (AW bits fill [0, DEPTH))."""
    cases = list(NEGATIVE_CASES)
    if _is_pow2(variant.depth):
        skipped = [c for c in cases if c.startswith("oor_")]
        cases = [c for c in cases if not c.startswith("oor_")]
        for case in skipped:
            print(
                f"SKIP {variant.module} {case}: DEPTH={variant.depth} is 2^AW; "
                "no out-of-range encoding fits on waddr/raddr",
                flush=True,
            )
    return cases


@pytest.mark.sim
@pytest.mark.parametrize("netlist", ["product", "hooks"])
def test_rtl_positive_all_variants(netlist):
    variants = _require_sim(netlist)
    from tb.cmn.sim_runner import run_sim_variant

    print(f"SEED {SEED}", flush=True)
    for variant in variants:
        for anur in (True, False):
            for case in POSITIVE_CASES:
                run_sim_variant(
                    variant,
                    case=case,
                    assert_no_uninit_read=anur,
                    seed=SEED,
                )


@pytest.mark.sim
@pytest.mark.parametrize("netlist", ["product", "hooks"])
def test_rtl_negative_all_variants(netlist):
    variants = _require_sim(netlist)
    from tb.cmn.sim_runner import run_sim_variant

    print(f"SEED {SEED}", flush=True)
    for variant in variants:
        for case in _negative_cases_for(variant):
            run_sim_variant(
                variant,
                case=case,
                assert_no_uninit_read=True,
                seed=SEED,
            )
        run_sim_variant(
            variant,
            case="uninit_ok",
            assert_no_uninit_read=False,
            seed=SEED,
        )
