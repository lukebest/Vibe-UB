#!/usr/bin/env python3
"""GATE-SYN-DEADREG: FF Q that cannot reach any output via transitive fanout.

On the DUT itself: flatten, no opt_clean. A flop is dead if none of its Q
bits reaches an output port through combo / other-cell fanout. Extra keep
registers that only feed themselves fail this check.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

_LOOP_TEMP = re.compile(r"^(by|bi|i|j|k|n|t|idx|cnt)$", re.I)

FF_TYPES = {
    "$dff",
    "$dffe",
    "$ff",
    "$sdff",
    "$sdffe",
    "$sdffce",
    "$adff",
    "$adffe",
    "$dffsr",
    "$dffsre",
    "$aldff",
}

# Yosys cell output pins. Everything else on the cell is treated as an input.
OUT_PINS = {"Q", "q", "Y", "BUF", "CO", "X", "P", "Y2", "Q_N"}


def _bits(conn: object) -> list:
    if not isinstance(conn, list):
        return []
    return [b for b in conn if b is not None]


def leftover_pyc_reg(mod: dict) -> list[str]:
    names = []
    for cname, cell in (mod.get("cells") or {}).items():
        t = (cell.get("type") or "").lstrip("\\")
        if t == "pyc_reg":
            names.append(cname)
    return names


def _q_names(mod: dict, q_bits: list) -> list[str]:
    target = tuple(q_bits)
    names = []
    for name, info in (mod.get("netnames") or {}).items():
        if info.get("hide_name"):
            continue
        raw = name[1:] if name.startswith("\\") else name
        if raw.startswith("$"):
            continue
        if tuple(info.get("bits") or []) == target:
            raw = name[1:] if name.startswith("\\") else name
            if "$" in raw:
                continue
            last = raw.replace("/", ".").split(".")[-1]
            if _LOOP_TEMP.fullmatch(last):
                continue
            names.append(name)
    return sorted(names)


def extract_ff_q(mod: dict) -> list[tuple[str, str, list, list[str]]]:
    found = []
    for cname, cell in (mod.get("cells") or {}).items():
        t = cell.get("type") or ""
        if t not in FF_TYPES:
            continue
        conns = cell.get("connections") or {}
        q = _bits(conns.get("Q") or conns.get("q") or [])
        found.append((cname, t, q, _q_names(mod, q)))
    return found


def output_bits(mod: dict) -> set:
    out: set = set()
    for _name, info in (mod.get("ports") or {}).items():
        if info.get("direction") == "output":
            out.update(_bits(info.get("bits") or []))
    return out


def fanout_map(mod: dict) -> dict[object, list[object]]:
    """bit → bits driven by cells that consume this bit."""
    fwd: dict[object, list[object]] = defaultdict(list)
    for _cname, cell in (mod.get("cells") or {}).items():
        conns = cell.get("connections") or {}
        ins: list = []
        outs: list = []
        for pin, bits in conns.items():
            bb = _bits(bits)
            if pin in OUT_PINS:
                outs.extend(bb)
            else:
                ins.extend(bb)
        for b in ins:
            fwd[b].extend(outs)
    return fwd


def q_reaches_output(q_bits: list, po: set, fwd: dict[object, list[object]]) -> bool:
    if any(b in po for b in q_bits):
        return True
    seen = set()
    stack = list(q_bits)
    while stack:
        b = stack.pop()
        if b in seen:
            continue
        seen.add(b)
        if b in po:
            return True
        for nxt in fwd.get(b, ()):
            if nxt not in seen:
                stack.append(nxt)
    return False


def find_dead_flops(mod: dict) -> list[dict]:
    po = output_bits(mod)
    fwd = fanout_map(mod)
    dead = []
    for cname, ftype, qbits, qnames in extract_ff_q(mod):
        if not qnames:
            # No public Q name: Yosys function/proc leftover, not an architectural FF.
            continue
        if not qbits:
            dead.append({"cell": cname, "type": ftype, "q": "-", "reason": "no_q_bits"})
            continue
        if not q_reaches_output(qbits, po, fwd):
            dead.append(
                {
                    "cell": cname,
                    "type": ftype,
                    "q": ",".join(qnames) or "-",
                    "reason": "q_no_path_to_output",
                }
            )
    return dead


def flatten_json(verilog: Path, top: str, incdirs: list[Path]) -> dict:
    inc = "".join(f" -I{d}" for d in incdirs if d.is_dir())
    with tempfile.TemporaryDirectory(prefix="deadreg_") as td:
        js = Path(td) / "dut.json"
        ys = (
            f"read_verilog -sv{inc} {verilog}\n"
            f"hierarchy -check -top {top}\n"
            "proc; flatten\n"
            f"write_json {js}\n"
        )
        proc = subprocess.run(
            ["yosys", "-q", "-p", ys],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if proc.returncode != 0 or not js.is_file():
            raise SystemExit(proc.stdout or f"deadreg flatten failed rc={proc.returncode}")
        data = json.loads(js.read_text(encoding="utf-8"))
    mods = data.get("modules") or {}
    if top in mods:
        return mods[top]
    if len(mods) == 1:
        return next(iter(mods.values()))
    raise SystemExit(f"deadreg: module {top} not in JSON ({list(mods)})")


def report(mod: dict, label: str) -> int:
    pyc = leftover_pyc_reg(mod)
    if pyc:
        print(f"equiv_ref DEADREG FAIL {label} leftover_pyc_reg={','.join(pyc)}")
        print("equiv_ref DEADREG note: flatten first so pyc_reg becomes $dff")
        return 1
    dead = find_dead_flops(mod)
    nff = sum(1 for _c, _t, _q, names in extract_ff_q(mod) if names)
    print(f"equiv_ref DEADREG label={label} flops={nff} dead={len(dead)}")
    for row in dead:
        print(
            f"equiv_ref DEADREG dead cell={row['cell']} type={row['type']} "
            f"q={row.get('q', '-')} reason={row['reason']}"
        )
    if dead:
        print(f"equiv_ref DEADREG result=FAIL ({len(dead)} flop Q cannot reach any output)")
        return 1
    print("equiv_ref DEADREG result=PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    ap.add_argument("--top", default="")
    ap.add_argument("--v", type=Path, help="Verilog DUT (flatten, no opt_clean)")
    ap.add_argument("--inc", action="append", default=[], help="include dir")
    ap.add_argument("--label", default="dut")
    args = ap.parse_args()
    if args.json:
        data = json.loads(args.json.read_text(encoding="utf-8"))
        mods = data.get("modules") or {}
        top = args.top or (next(iter(mods)) if mods else "")
        if top not in mods:
            raise SystemExit(f"deadreg: --top {top} not in {args.json}")
        return report(mods[top], args.label)
    if args.v:
        if not args.top:
            raise SystemExit("deadreg --v needs --top")
        inc = [Path(p) for p in args.inc]
        return report(flatten_json(args.v, args.top, inc), args.label)
    raise SystemExit("deadreg: need --json or --v")


if __name__ == "__main__":
    raise SystemExit(main())
