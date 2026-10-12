"""Build and run Verilator + cocotb for ``ub_tp_bypass`` (PRODUCT and HOOKS)."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path

from tb.cmn.discover import PycLibError, pyc_lib_dir, require_pyc_runtime, used_pyc_lib_files
from tb.tp.ports import HOOKS, LEAF, PRODUCT, check_ports

TB_TP = Path(__file__).resolve().parent
REPO_ROOT = TB_TP.parents[1]
SIM_MODULE = "tb.tp.sim_scoreboard_cocotb"
_LAYER_PYC_MARKERS = ("/rtl/tp/pyc_", "/rtl/tp/hooks/pyc_")


def _netlist_path(netlist: str) -> Path:
    if netlist == "hooks":
        path = HOOKS
    elif netlist == "product":
        path = PRODUCT
    else:
        raise ValueError(f"unknown netlist {netlist!r}")
    if not path.is_file():
        raise AssertionError(f"missing {path}")
    check_ports(path.read_text(encoding="utf-8"))
    return path


def _verilog_sources(leaf: Path) -> list[Path]:
    require_pyc_runtime()
    used = used_pyc_lib_files(leaf)
    by_stem: dict[str, Path] = {}
    for path in used:
        resolved = path.resolve()
        text = str(resolved)
        if any(mark in text for mark in _LAYER_PYC_MARKERS):
            raise PycLibError(
                f"仿真文件列表拒绝层目录运行库 {resolved}；应使用 rtl/pyc_lib/"
            )
        by_stem[resolved.stem] = resolved
    out = [leaf.resolve()]
    out.extend(by_stem[name] for name in sorted(by_stem))
    return out


def _clear_stale_results(build_dir: Path) -> None:
    if not build_dir.is_dir():
        return
    for path in build_dir.iterdir():
        if path.is_file() and (
            path.name == "results.xml" or path.name.endswith(".None")
        ):
            path.unlink()


def _find_cocotb_results(build_dir: Path) -> Path:
    named = build_dir / "results.xml"
    if named.is_file():
        return named
    extras = [
        p
        for p in build_dir.iterdir()
        if p.is_file()
        and p.stat().st_size > 0
        and (p.suffix == ".xml" or p.name.endswith(".None"))
    ]
    if extras:
        return sorted(extras)[-1]
    raise AssertionError(f"cocotb results.xml missing under {build_dir}")


def _assert_cocotb_passed(build_dir: Path) -> None:
    xml = _find_cocotb_results(build_dir)
    root = ET.parse(xml).getroot()
    fails = list(root.iter("failure")) + list(root.iter("error"))
    if fails:
        texts = []
        for node in fails:
            texts.append((node.get("message") or node.text or "failure").strip())
        raise AssertionError(
            f"cocotb reported {len(fails)} failure(s) in {xml}: "
            + " | ".join(texts)
        )


def run_sim(
    netlist: str,
    *,
    case: str = "all",
    seed: int = 1,
) -> None:
    from cocotb.runner import get_runner

    require_pyc_runtime()
    leaf = _netlist_path(netlist)
    build_dir = TB_TP / "sim_build" / f"{netlist}_{LEAF}_{case}"
    build_dir.mkdir(parents=True, exist_ok=True)
    _clear_stale_results(build_dir)

    extra_env = {
        "TP_CASE": case,
        "TP_SEED": str(int(seed)),
        "TP_NETLIST": netlist,
        "COCOTB_RESULTS_FILE": str(build_dir / "results.xml"),
        "PYTHONPATH": (
            str(REPO_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")
        ).rstrip(os.pathsep),
    }
    pyc_lib = pyc_lib_dir().resolve()
    build_args = [
        "--timescale",
        "1ns/1ps",
        "-Wno-fatal",
        "-Wno-UNUSED",
        "-Wno-UNUSEDPARAM",
        "-Wno-DECLFILENAME",
        "-Wno-UNOPTFLAT",
        f"-I{pyc_lib}",
    ]
    srcs = [
        str(p)
        for p in _verilog_sources(leaf)
        if not (p.name.startswith("pyc_") and p.suffix.lower() in {".v", ".sv"})
    ]
    runner = get_runner("verilator")
    build_kw = dict(
        hdl_toplevel=LEAF,
        always=False,
        build_dir=str(build_dir),
        includes=[str(pyc_lib)],
        build_args=build_args,
    )
    try:
        runner.build(verilog_sources=srcs, **build_kw)
    except TypeError:
        runner.build(sources=srcs, **build_kw)

    test_kw = dict(
        hdl_toplevel=LEAF,
        test_module=SIM_MODULE,
        extra_env=extra_env,
        plusargs=[f"+SEED={int(seed)}"],
    )
    try:
        try:
            runner.test(**test_kw)
        except TypeError:
            runner.test(
                hdl_toplevel=LEAF, test_module=SIM_MODULE, extra_env=extra_env
            )
    except SystemExit:
        _assert_cocotb_passed(build_dir)
        raise
    _assert_cocotb_passed(build_dir)


__all__ = ["run_sim"]
