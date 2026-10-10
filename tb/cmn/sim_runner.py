"""Build and run Verilator + cocotb for one discovered fixed-netlist variant.

No Verilator ``-G``. DEPTH/WIDTH are parsed from the variant and baked into a
generated wrapper. Equivalence (PRODUCT vs HOOKS) is a gate Yosys-equiv job,
not this TB.
"""

from __future__ import annotations

import os
from pathlib import Path

from tb.cmn.discover import (
    REPO_ROOT,
    MemVariant,
    rtl_sim_skip_reason,
)
from tb.cmn.harness.emit_wrapper import TOPLEVEL, emit_wrapper
from tb.cmn.sequences import expected_violation

TB_CMN = Path(__file__).resolve().parent
FORMAL_PROPS = REPO_ROOT / "formal" / "cmn" / "ub_cmn_mem_1r1w_if_props.sv"
SIM_MODULE = "tb.cmn.sim_cocotb"


def _build_and_test(
    variant: MemVariant,
    *,
    assert_no_uninit_read: bool,
    case: str,
    seed: int,
    tb_check: bool,
) -> None:
    from cocotb.runner import get_runner

    build_dir = (
        TB_CMN
        / "sim_build"
        / f"{variant.netlist}_{variant.module}_a{int(assert_no_uninit_read)}_c{int(tb_check)}"
    )
    build_dir.mkdir(parents=True, exist_ok=True)
    wrapper = emit_wrapper(
        build_dir / "ub_cmn_mem_1r1w_tb.sv",
        dut_module=variant.module,
        depth=variant.depth,
        width=variant.width,
        assert_no_uninit_read=assert_no_uninit_read,
        tb_check=tb_check,
    )

    sources = [wrapper, variant.path]
    if tb_check and FORMAL_PROPS.is_file():
        sources.append(FORMAL_PROPS)

    extra_env = {
        "CMN_CASE": case,
        "CMN_SEED": str(int(seed)),
        "CMN_DEPTH": str(int(variant.depth)),
        "CMN_WIDTH": str(int(variant.width)),
        "CMN_ASSERT_NO_UNINIT_READ": str(int(bool(assert_no_uninit_read))),
        "CMN_VARIANT": variant.module,
        "CMN_NETLIST": variant.netlist,
        "PYTHONPATH": (
            str(REPO_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")
        ).rstrip(os.pathsep),
    }
    build_args = [
        "--timescale",
        "1ns/1ps",
        "-Wno-fatal",
        "-Wno-UNUSED",
        "-Wno-UNUSEDPARAM",
        "-Wno-DECLFILENAME",
        "-Wno-UNOPTFLAT",
        "--assert",
    ]
    includes = [str(variant.path.parent), str(REPO_ROOT / "formal" / "cmn")]

    runner = get_runner("verilator")
    # Do not pass `parameters=` — that becomes Verilator -G (forbidden).
    build_kw = dict(
        hdl_toplevel=TOPLEVEL,
        always=True,
        build_dir=str(build_dir),
        includes=includes,
        build_args=build_args,
    )
    srcs = [str(p) for p in sources]
    try:
        runner.build(verilog_sources=srcs, **build_kw)
    except TypeError:
        runner.build(sources=srcs, **build_kw)

    test_kw = dict(
        hdl_toplevel=TOPLEVEL,
        test_module=SIM_MODULE,
        extra_env=extra_env,
        plusargs=[f"+SEED={int(seed)}"],
    )
    try:
        runner.test(**test_kw)
    except TypeError:
        runner.test(hdl_toplevel=TOPLEVEL, test_module=SIM_MODULE, extra_env=extra_env)


def run_sim_variant(
    variant: MemVariant,
    *,
    case: str,
    assert_no_uninit_read: bool,
    seed: int = 1,
) -> None:
    reason = rtl_sim_skip_reason(netlist=variant.netlist)
    if reason:
        raise RuntimeError(reason)
    want = expected_violation(case, assert_no_uninit_read)
    _build_and_test(
        variant,
        assert_no_uninit_read=assert_no_uninit_read,
        case=case,
        seed=seed,
        tb_check=want is None,
    )
