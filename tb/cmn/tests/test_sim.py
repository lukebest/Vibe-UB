"""cocotb + Verilator against discovered fixed netlists (SPEC §2.2).

Skipped with an explicit reason when ``rtl/cmn/`` (PRODUCT) or
``rtl/cmn/hooks/`` (TEST_HOOKS) has no parseable variants, or when
Verilator / cocotb is missing. Equivalence of the two netlists is a
gate Yosys-equiv job — this file does not run eqy.

``d64w64m16`` runs the full suite (word + segmented). ``d512w512m64``
is smoke only (short random + a few directed cases). Both PRODUCT and
HOOKS are attempted; a missing hooks tree or segmented leaf is skip
with the gap named.
"""

from __future__ import annotations

import pytest

from tb.cmn.discover import discover_by_netlist, rtl_sim_skip_reason
from tb.cmn.sequences import (
    FULL_WMASK_TAGS,
    NEGATIVE_CASES,
    POSITIVE_CASES,
    SMOKE_CASES,
    SMOKE_RANDOM_N,
    SMOKE_WMASK_TAGS,
    WMASK_CASES,
    WMASK_NEG_CASES,
)

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
    return variants


def _is_pow2(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def _is_smoke(variant) -> bool:
    return variant.tag in SMOKE_WMASK_TAGS or (
        variant.depth >= 512 and variant.width >= 512 and variant.nseg > 1
    )


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
        skipped = [c for c in cases if c.startswith("oor_")]
        cases = [c for c in cases if not c.startswith("oor_")]
        for case in skipped:
            print(
                f"SKIP {variant.module} {case}: DEPTH={variant.depth} is 2^AW; "
                "no out-of-range encoding fits on waddr/raddr",
                flush=True,
            )
    return cases


def _note_wmask_coverage(variants) -> None:
    tags = {v.tag for v in variants}
    if "d64w64m16" not in tags and not any(v.nseg > 1 and not _is_smoke(v) for v in variants):
        print(
            "NOTE: no full-suite segmented leaf (expected d64w64m16) in this netlist",
            flush=True,
        )
    if "d512w512m64" not in tags and not any(_is_smoke(v) for v in variants):
        print(
            "NOTE: no smoke segmented leaf (expected d512w512m64) in this netlist",
            flush=True,
        )
    for name in sorted(FULL_WMASK_TAGS | SMOKE_WMASK_TAGS):
        if name not in tags:
            print(f"NOTE: variant {name} not discovered", flush=True)


@pytest.mark.sim
@pytest.mark.parametrize("netlist", ["product", "hooks"])
def test_rtl_positive_all_variants(netlist):
    variants = _require_sim(netlist)
    from tb.cmn.sim_runner import run_sim_variant

    print(f"SEED {SEED}", flush=True)
    _note_wmask_coverage(variants)
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
                f"SKIP {variant.module} negatives: smoke suite only "
                "(d512w512m64 / large segmented leaf)",
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
