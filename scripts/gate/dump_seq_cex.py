#!/usr/bin/env python3
"""Dump Yosys sat sequential miter CEX (inputs + both-side outputs per step)."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def gold_files(leaf: str) -> list[Path]:
    if leaf == "ub_dll_bcrc_check":
        return [
            ROOT / "formal/dll/ref/ub_dll_bcrc.sv",
            ROOT / "formal/dll/ref/ub_dll_bcrc_check.sv",
        ]
    if leaf == "ub_dll_bcrc":
        return [ROOT / "formal/dll/ref/ub_dll_bcrc.sv"]
    if leaf == "ub_pyc_rst_adapt":
        return [ROOT / "formal/common/ref/ub_pyc_rst_adapt.sv"]
    layer = "pcs" if "lane" in leaf else "dll"
    return [ROOT / f"formal/{layer}/ref/{leaf}.sv"]


def inc_flags(net: Path) -> str:
    bits = []
    for d in (ROOT / "rtl/pyc_lib", ROOT / "rtl/common", net.parent):
        if d.is_dir():
            bits.append(f"-I{d}")
    return " ".join(bits)


def build_script(
    leaf: str,
    net: Path,
    tmp: Path,
    depth: int,
    tmo: int,
    extra_sat: str,
) -> str:
    reads_g = "\n".join(f"read_verilog -sv {p}" for p in gold_files(leaf))
    inc = inc_flags(net)
    vcd = tmp / "cex.vcd"
    return f"""
{reads_g}
hierarchy -check -top {leaf}
rename -top gold
proc; flatten; opt_expr; opt_clean
design -stash gold
read_verilog -sv {inc} {net}
hierarchy -check -top {leaf}
rename -top gate
proc; flatten; opt_expr; opt_clean
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
miter -equiv -flatten -make_assert gold gate miter
hierarchy -top miter
sat -seq {depth} -verify -prove-asserts -prove-skip 2 -set-at 1 in_rst_pyc 1 -set-at 2 in_rst_pyc 1 -show-inputs -show-outputs -show-regs -dump_vcd {vcd} -timeout {tmo} {extra_sat}
"""


def run_yosys(script: str, tmo: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["timeout", str(tmo + 10), "yosys", "-p", script],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def parse_sat_model(log: str) -> list[dict[str, str]]:
    """Yosys sat prints '  signal = value' blocks per timestep / Sat timestep."""
    steps: list[dict[str, str]] = []
    cur: dict[str, str] = {}
    step_i = 0
    for line in log.splitlines():
        if re.search(r"Time step|timestep|Sat timestep|Step \d", line, re.I):
            if cur:
                steps.append(cur)
                cur = {}
            m = re.search(r"(\d+)", line)
            step_i = int(m.group(1)) if m else step_i + 1
            cur["_step"] = str(step_i)
            continue
        m = re.search(r"^\s*(\\?[A-Za-z0-9_./\[\]]+)\s*=\s*(.+?)\s*$", line)
        if m and cur is not None:
            name = m.group(1).lstrip("\\")
            cur[name] = m.group(2).strip().rstrip(".")
    if cur:
        steps.append(cur)
    return steps


def interesting(name: str) -> bool:
    keys = (
        "rst", "start", "valid", "last", "data_in", "crc_word", "done",
        "trigger", "ok", "fail", "recv", "eflag", "core_clk", "crc",
    )
    low = name.lower()
    return any(k in low for k in keys)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--leaf", required=True)
    ap.add_argument("--net", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--depth", type=int, default=6)
    ap.add_argument("--tmo", type=int, default=40)
    ap.add_argument("--extra-sat", default="")
    args = ap.parse_args()
    net = Path(args.net)
    tmp = Path("/tmp") / f"seq_cex_{args.label or args.leaf}"
    tmp.mkdir(parents=True, exist_ok=True)
    script = build_script(args.leaf, net, tmp, args.depth, args.tmo, args.extra_sat)
    (tmp / "dump.ys").write_text(script, encoding="utf-8")
    print(f"DUMP leaf={args.leaf} net={net} depth={args.depth} tmp={tmp}")
    proc = run_yosys(script, args.tmo)
    log = proc.stdout or ""
    (tmp / "yosys.log").write_text(log, encoding="utf-8")
    print(f"DUMP rc={proc.returncode}")
    for line in log.splitlines():
        if re.search(
            r"proof did|SAT proof|Assert failed|timeout|Time step|model found|FAILED|SUCCESS",
            line,
            re.I,
        ):
            print(f"DUMP line={line.strip()}")
    steps = parse_sat_model(log)
    print(f"DUMP steps_parsed={len(steps)} vcd={(tmp / 'cex.vcd').is_file()}")
    if not steps:
        # print a tail so we can see the format
        tail = [ln for ln in log.splitlines() if ln.strip()][-40:]
        print("DUMP log_tail:")
        for ln in tail:
            print(ln)
        return proc.returncode
    for st in steps:
        keys = [k for k in st if k == "_step" or interesting(k)]
        parts = [f"{k}={st[k]}" for k in sorted(keys, key=lambda x: (x != "_step", x))]
        print("DUMP step " + " ".join(parts))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
