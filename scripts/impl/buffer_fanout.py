#!/usr/bin/env python3
"""Deterministic high-fanout buffer trees on a Yosys JSON netlist.

After abc mapping, insert sky130_fd_sc_hd__buf_4 / buf_8 trees so no
non-clock data net has more than ``max_fanout`` sinks. Used by impl
quick-synth when OpenROAD ``repair_design`` is not available.

Clock / reset ports and sequential CLK/GATE pins are left unbuffered
(STA uses an ideal clock; reset is a false path).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

BUF4 = "sky130_fd_sc_hd__buf_4"
BUF8 = "sky130_fd_sc_hd__buf_8"
BUF_IN = "A"
BUF_OUT = "X"

DEFAULT_MAX_FANOUT = 16

CLOCK_PORT_RE = re.compile(
    r"^(core_clk|clk|clock|clk_i|gclk)$", re.IGNORECASE
)
RESET_PORT_RE = re.compile(
    r"^(rst_n|rst_pyc|rst|reset|reset_n|port_rst)$", re.IGNORECASE
)
CLOCK_PIN_RE = re.compile(r"^(CLK|CLK_N|GATE)$")


def _is_bit(x: Any) -> bool:
    return isinstance(x, int)


def _sanitize(name: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", name or "n")
    s = re.sub(r"_+", "_", s).strip("_")
    if not s or s[0].isdigit():
        s = "n_" + s
    return s[:n]


def choose_buf(n_loads: int) -> str:
    """buf_4 for small leftover groups; buf_8 otherwise (max fanout 16)."""
    if n_loads <= 4:
        return BUF4
    return BUF8


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    if size < 2:
        size = 2
    return [items[i : i + size] for i in range(0, len(items), size)]


def _all_int_bits(mod: dict[str, Any]) -> set[int]:
    bits: set[int] = set()
    for port in (mod.get("ports") or {}).values():
        for b in port.get("bits") or []:
            if _is_bit(b):
                bits.add(b)
    for cell in (mod.get("cells") or {}).values():
        for conn in (cell.get("connections") or {}).values():
            for b in conn:
                if _is_bit(b):
                    bits.add(b)
    for net in (mod.get("netnames") or {}).values():
        for b in net.get("bits") or []:
            if _is_bit(b):
                bits.add(b)
    return bits


def _bit_netname(mod: dict[str, Any], bit: int) -> str:
    for name, net in (mod.get("netnames") or {}).items():
        bits = net.get("bits") or []
        if bit in bits:
            return str(name)
    return f"w{bit}"


def _port_bits_named(mod: dict[str, Any], pred) -> set[int]:
    out: set[int] = set()
    for name, port in (mod.get("ports") or {}).items():
        if pred(name):
            for b in port.get("bits") or []:
                if _is_bit(b):
                    out.add(b)
    return out


def analyze_module(mod: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Map bit -> {drivers, sinks, fanout, skip_reason}."""
    clock_bits = _port_bits_named(mod, lambda n: bool(CLOCK_PORT_RE.match(n)))
    reset_bits = _port_bits_named(mod, lambda n: bool(RESET_PORT_RE.match(n)))

    info: dict[int, dict[str, Any]] = {}

    def rec(bit: int) -> dict[str, Any]:
        if bit not in info:
            info[bit] = {
                "drivers": [],
                "sinks": [],
                "fanout": 0,
                "skip_reason": None,
            }
        return info[bit]

    for pname, port in (mod.get("ports") or {}).items():
        direction = (port.get("direction") or "").lower()
        for idx, b in enumerate(port.get("bits") or []):
            if not _is_bit(b):
                continue
            slot = ("port", pname, idx, direction)
            if direction == "input":
                rec(b)["drivers"].append(slot)
            elif direction == "output":
                rec(b)["sinks"].append(slot)
            else:
                rec(b)["drivers"].append(slot)
                rec(b)["sinks"].append(slot)

    for cname, cell in (mod.get("cells") or {}).items():
        dirs = cell.get("port_directions") or {}
        ctype = cell.get("type") or ""
        for pin, conn in (cell.get("connections") or {}).items():
            pdir = (dirs.get(pin) or "").lower()
            if not pdir:
                # Sky130 hd: A/B/C/D/RESET_B/SET_B/CLK/GATE input; X/Y/Q/QN out.
                if pin in {"X", "Y", "Q", "QN", "COUT", "SUM"}:
                    pdir = "output"
                else:
                    pdir = "input"
            for idx, b in enumerate(conn):
                if not _is_bit(b):
                    continue
                slot = ("cell", cname, pin, idx, ctype)
                if pdir == "output":
                    rec(b)["drivers"].append(slot)
                elif pdir == "input":
                    rec(b)["sinks"].append(slot)
                else:
                    rec(b)["drivers"].append(slot)
                    rec(b)["sinks"].append(slot)

    for bit, recd in info.items():
        recd["fanout"] = len(recd["sinks"])
        if bit in clock_bits or CLOCK_PORT_RE.match(_bit_netname(mod, bit)):
            recd["skip_reason"] = "clock"
        elif bit in reset_bits:
            recd["skip_reason"] = "reset"
        elif any(
            s[0] == "cell" and CLOCK_PIN_RE.match(str(s[2])) for s in recd["sinks"]
        ):
            recd["skip_reason"] = "clock_pin"
        elif any(
            s[0] == "cell" and CLOCK_PIN_RE.match(str(s[2])) for s in recd["drivers"]
        ):
            recd["skip_reason"] = "clock_pin"
    return info


def max_fanout(mod: dict[str, Any], *, include_skipped: bool = True) -> int:
    info = analyze_module(mod)
    vals = [
        r["fanout"]
        for r in info.values()
        if include_skipped or not r["skip_reason"]
    ]
    return max(vals, default=0)


def _set_sink_bit(
    mod: dict[str, Any], sink: tuple[Any, ...], new_bit: int
) -> None:
    kind = sink[0]
    if kind == "port":
        _, pname, idx, _d = sink
        bits = list(mod["ports"][pname]["bits"])
        bits[idx] = new_bit
        mod["ports"][pname]["bits"] = bits
        net = (mod.get("netnames") or {}).get(pname)
        if net and idx < len(net.get("bits") or []):
            nb = list(net["bits"])
            nb[idx] = new_bit
            net["bits"] = nb
        return
    _, cname, pin, idx, _t = sink
    conn = list(mod["cells"][cname]["connections"][pin])
    conn[idx] = new_bit
    mod["cells"][cname]["connections"][pin] = conn


def _add_buf(
    mod: dict[str, Any],
    name: str,
    buf_type: str,
    in_bit: int,
    out_bit: int,
) -> None:
    cells = mod.setdefault("cells", {})
    cells[name] = {
        "hide_name": 1,
        "type": buf_type,
        "parameters": {},
        "attributes": {"qs_fanout_buf": "00000000000000000000000000000001"},
        "port_directions": {BUF_IN: "input", BUF_OUT: "output"},
        "connections": {BUF_IN: [in_bit], BUF_OUT: [out_bit]},
    }
    nets = mod.setdefault("netnames", {})
    nets[name + "_z"] = {
        "hide_name": 1,
        "bits": [out_bit],
        "attributes": {},
    }


def _sink_sort_key(s: tuple[Any, ...]) -> tuple[Any, ...]:
    return s


def _buffer_one_net(
    mod: dict[str, Any],
    bit: int,
    sinks: list[tuple[Any, ...]],
    max_fo: int,
    name_prefix: str,
    alloc_bit,
    used_names: set[str],
) -> int:
    """Return number of buffers inserted. Mutates ``mod``."""
    sinks = sorted(sinks, key=_sink_sort_key)
    if len(sinks) <= max_fo:
        return 0

    n_added = 0
    level = 0
    current = sinks
    while len(current) > max_fo:
        groups = _chunks(current, max_fo)
        nxt: list[tuple[Any, ...]] = []
        for gi, group in enumerate(groups):
            out_bit = alloc_bit()
            inst = f"{name_prefix}_L{level}_{gi}"
            n = 2
            while inst in used_names:
                inst = f"{name_prefix}_L{level}_{gi}_{n}"
                n += 1
            used_names.add(inst)
            # Leaf/mid buffers drive ``group``; their A pins become the
            # next level's sinks. The original driver is wired last.
            _add_buf(mod, inst, choose_buf(len(group)), bit, out_bit)
            n_added += 1
            for snk in group:
                _set_sink_bit(mod, snk, out_bit)
            nxt.append(("cell", inst, BUF_IN, 0, choose_buf(len(group))))
        current = nxt
        level += 1
    # ``current`` is now the first-level buffer A pins (or leftover);
    # they stay on the original ``bit``.
    return n_added


def buffer_module(
    mod: dict[str, Any], max_fanout_limit: int = DEFAULT_MAX_FANOUT
) -> dict[str, Any]:
    """Insert trees in place. Return a report dict."""
    info = analyze_module(mod)
    before = max((r["fanout"] for r in info.values()), default=0)
    bits_state = _all_int_bits(mod)
    next_bit = (max(bits_state) + 1) if bits_state else 2

    def alloc_bit() -> int:
        nonlocal next_bit
        b = next_bit
        next_bit += 1
        return b

    used_names = set(mod.get("cells") or {})
    n_bufs = 0
    n_nets = 0
    # Stable order: by bit id, then name.
    work = []
    for bit, rec in info.items():
        if rec["skip_reason"]:
            continue
        if rec["fanout"] <= max_fanout_limit:
            continue
        if len(rec["drivers"]) != 1:
            continue
        work.append((bit, rec))
    work.sort(key=lambda x: (x[0], _bit_netname(mod, x[0])))

    for bit, rec in work:
        prefix = "qs_fbuf_" + _sanitize(_bit_netname(mod, bit))
        added = _buffer_one_net(
            mod,
            bit,
            list(rec["sinks"]),
            max_fanout_limit,
            prefix,
            alloc_bit,
            used_names,
        )
        if added:
            n_bufs += added
            n_nets += 1

    after_info = analyze_module(mod)
    after = max((r["fanout"] for r in after_info.values()), default=0)
    after_data = max(
        (
            r["fanout"]
            for r in after_info.values()
            if not r["skip_reason"]
        ),
        default=0,
    )
    return {
        "max_fanout_before": before,
        "max_fanout_after": after,
        "max_fanout_after_data": after_data,
        "n_nets_buffered": n_nets,
        "n_bufs": n_bufs,
        "max_fanout_limit": max_fanout_limit,
        "method": "yosys_buf_tree",
    }


def buffer_design(
    data: dict[str, Any], max_fanout_limit: int = DEFAULT_MAX_FANOUT
) -> tuple[dict[str, Any], dict[str, Any]]:
    reports = {}
    worst_before = 0
    worst_after = 0
    n_bufs = 0
    n_nets = 0
    for name, mod in (data.get("modules") or {}).items():
        rep = buffer_module(mod, max_fanout_limit)
        reports[name] = rep
        worst_before = max(worst_before, int(rep["max_fanout_before"]))
        worst_after = max(worst_after, int(rep["max_fanout_after"]))
        n_bufs += int(rep["n_bufs"])
        n_nets += int(rep["n_nets_buffered"])
    summary = {
        "max_fanout_before": worst_before,
        "max_fanout_after": worst_after,
        "n_nets_buffered": n_nets,
        "n_bufs": n_bufs,
        "max_fanout_limit": max_fanout_limit,
        "method": "yosys_buf_tree",
        "modules": reports,
    }
    return data, summary


def analyze_design(data: dict[str, Any]) -> dict[str, Any]:
    worst = 0
    mods = {}
    for name, mod in (data.get("modules") or {}).items():
        fo = max_fanout(mod)
        mods[name] = {"max_fanout": fo}
        worst = max(worst, fo)
    return {
        "max_fanout_before": worst,
        "max_fanout_after": worst,
        "n_nets_buffered": 0,
        "n_bufs": 0,
        "method": "none",
        "modules": mods,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, help="write buffered JSON (omit = report only)")
    ap.add_argument("--report", type=Path, help="write fanout_report.json")
    ap.add_argument(
        "--max-fanout",
        type=int,
        default=DEFAULT_MAX_FANOUT,
        help=f"max sinks per driver (default {DEFAULT_MAX_FANOUT})",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="insert buffers (default if --out is set)",
    )
    args = ap.parse_args(argv)
    data = json.loads(args.inp.read_text(encoding="utf-8"))
    apply = bool(args.out) or args.apply
    if apply:
        data, summary = buffer_design(data, args.max_fanout)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(data, indent=2) + "\n", encoding="utf-8"
            )
    else:
        summary = analyze_design(data)
        summary["max_fanout_limit"] = args.max_fanout
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"fanout before={summary['max_fanout_before']} "
        f"after={summary['max_fanout_after']} "
        f"bufs={summary['n_bufs']} nets={summary['n_nets_buffered']} "
        f"method={summary['method']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
