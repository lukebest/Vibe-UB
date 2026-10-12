"""cocotb + Verilator against discovered fixed netlists (SPEC §2.2).

The matrix is whatever ``discover_variants()`` finds under ``rtl/cmn/``
(PRODUCT) and ``rtl/cmn/hooks/`` (TEST_HOOKS). There is no hardcoded
variant list. Arrays with ``DEPTH*WIDTH > 4096`` bits use a short smoke
plan; smaller ones run the full directed + random suite. A leaf that is
absent is simply not discovered — that is not a skip or a failure.

Skipped only when a whole netlist tree has no parseable variants, or
when Verilator / cocotb is missing. Equivalence of the two netlists is
a gate Yosys-equiv job — this file does not run eqy.
"""

from __future__ import annotations

import pytest

from tb.cmn.discover import discover_by_netlist, require_pyc_runtime, rtl_sim_skip_reason
from tb.cmn.sequences import (
    NEGATIVE_CASES,
    POSITIVE_CASES,
    SMOKE_CASES,
    SMOKE_RANDOM_N,
    WMASK_CASES,
    WMASK_NEG_CASES,
    is_smoke_variant,
)

SEED = 1


def _require_sim(netlist: str):
    # Missing rtl/pyc_lib/ or leftover layer pyc_* is a failure, not a skip.
    require_pyc_runtime()
    reason = rtl_sim_skip_reason(netlist=netlist)
    if reason:
        pytest.skip(reason)
    variants = discover_by_netlist(netlist)
    if not variants:
        pytest.skip(
            f"No {netlist} ub_cmn_mem_1r1w variants under rtl/cmn/ "
            "(SPEC §2.2). design-B has not landed the leaf."
        )
    return variants


def _is_pow2(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def _is_smoke(variant) -> bool:
    return is_smoke_variant(variant.depth, variant.width)


def _positive_plan(variant) -> tuple[list[str], tuple[bool, ...], int]:
    if _is_smoke(variant):
        cases = [c for c in SMOKE_CASES if c != "wmask_single" or variant.nseg > 1]
        return cases, (True,), SMOKE_RANDOM_N
    cases = list(POSITIVE_CASES)
    if variant.nseg > 1:
        cases.extend(WMASK_CASES)
    return cases, (True, False), 80


def _negative_cases_for(variant) -> list[str]:
    """OOR encodings do not exist when DEPTH is a power of two (AW bits fill [0, DEPTH))."""
    if _is_smoke(variant):
        return []
    cases = list(NEGATIVE_CASES)
    if variant.nseg > 1:
        cases.extend(WMASK_NEG_CASES)
    if _is_pow2(variant.depth):
        cases = [c for c in cases if not c.startswith("oor_")]
    return cases


def _log_discovered(variants) -> None:
    for var in variants:
        bits = var.depth * var.width
        print(
            f"DISCOVER {var.netlist}:{var.module} "
            f"DEPTH={var.depth} WIDTH={var.width} WMASK_W={var.wmask_w} "
            f"NSEG={var.nseg} bits={bits} "
            f"suite={'smoke' if _is_smoke(var) else 'full'}",
            flush=True,
        )


@pytest.mark.sim
@pytest.mark.parametrize("netlist", ["product", "hooks"])
def test_rtl_positive_all_variants(netlist):
    variants = _require_sim(netlist)
    from tb.cmn.sim_runner import run_sim_variant

    print(f"SEED {SEED}", flush=True)
    _log_discovered(variants)
    for variant in variants:
        cases, anurs, random_n = _positive_plan(variant)
        print(
            f"PLAN {variant.module} nseg={variant.nseg} "
            f"suite={'smoke' if _is_smoke(variant) else 'full'} "
            f"cases={cases} anur={list(anurs)} random_n={random_n}",
            flush=True,
        )
        for anur in anurs:
            for case in cases:
                run_sim_variant(
                    variant,
                    case=case,
                    assert_no_uninit_read=anur,
                    seed=SEED,
                    random_n=random_n,
                )


@pytest.mark.sim
@pytest.mark.parametrize("netlist", ["product", "hooks"])
def test_rtl_negative_all_variants(netlist):
    variants = _require_sim(netlist)
    from tb.cmn.sim_runner import run_sim_variant

    print(f"SEED {SEED}", flush=True)
    for variant in variants:
        if _is_smoke(variant):
            print(
                f"PLAN {variant.module} negatives omitted (smoke: "
                f"DEPTH*WIDTH={variant.depth * variant.width} > 4096)",
                flush=True,
            )
            continue
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
        if variant.nseg > 1:
            run_sim_variant(
                variant,
                case="wmask_partial_ok",
                assert_no_uninit_read=False,
                seed=SEED,
            )
