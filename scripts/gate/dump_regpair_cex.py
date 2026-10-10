#!/usr/bin/env python3
"""Dump the first rp_d_crc cut-point cex and classify Xia §2.6 gap vs mid-block.

For each net: pair/cut like equiv_regpair, eval directed reachable vectors,
then SAT on an isolated rp_d_crc miter. Print both sides' Q (crc / crc_word)
and inputs start/valid_in/last. Reachability is from reset (crc=INIT).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from equiv_regpair import (  # noqa: E402
    eval_signals,
    extract_flops,
    group_by_key,
    run_yosys_file,
    run_yosys_p,
    sat_kind,
    strip_ports_for,
    write_cut_script,
)

INIT = 0x3FFFFFFF
ROOT = Path(__file__).resolve().parents[2]


def prep_il(leaf: str, net: Path, tmp: Path, extra_gold: list[Path] | None = None) -> None:
    gold = ROOT / {
        "ub_dll_bcrc": "formal/dll/ref/ub_dll_bcrc.sv",
        "ub_dll_bcrc_check": "formal/dll/ref/ub_dll_bcrc_check.sv",
    }[leaf]
    golds = list(extra_gold or [])
    if leaf == "ub_dll_bcrc_check":
        golds.append(ROOT / "formal/dll/ref/ub_dll_bcrc.sv")
    golds.append(gold)
    inc = ""
    for d in (ROOT / "rtl/pyc_lib", ROOT / "rtl/common", net.parent):
        if d.is_dir():
            inc += f" -I{d}"
    reads_g = "\n".join(f"read_verilog -sv {p}" for p in golds)
    ys = (
        f"{reads_g}\n"
        f"hierarchy -check -top {leaf}\n"
        "rename -top gold\n"
        "proc; flatten; opt_expr; opt_clean; autoname\n"
        f"write_json {tmp / 'gold.json'}\n"
        f"write_rtlil {tmp / 'gold.il'}\n"
        "design -reset\n"
        f"read_verilog -sv{inc} {net}\n"
        f"hierarchy -check -top {leaf}\n"
        "rename -top gate\n"
        "proc; flatten; opt_expr; opt_clean; autoname\n"
        f"write_json {tmp / 'gate.json'}\n"
        f"write_rtlil {tmp / 'gate.il'}\n"
    )
    proc = run_yosys_p(ys, 90, quiet=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stdout or "prep failed")


def classify(start: int, valid: int, last: int) -> str:
    if valid:
        return "块中间" + (" (last 拍)" if last else "")
    if start:
        return "空档 (start-only, 无 valid)"
    return "上一块 last 之后、下一块首个 valid 之前的空档"


def reachable_from_reset(q_crc: int, start: int, valid: int, last: int) -> str:
    # After reset both sides hold crc=INIT, word=0, done=0.
    if q_crc == INIT:
        return "YES (复位后 crc=INIT；gold 在 last 后也回到 INIT)"
    if valid and not last:
        return "MAYBE (块中累积 remainder；需从 INIT 折入若干 valid)"
    if valid and last:
        return "MAYBE (若 Q 是上一拍 remainder；单 flit last 则 Q=INIT 才从复位一步到达)"
    return "UNREACHABLE-on-gold-after-last (gold last 后 crc=INIT；#5 可能留下 nxt)"


def dump_one(leaf: str, label: str, net: Path) -> None:
    print(f"\n======== {label} leaf={leaf} net={net} ========")
    with tempfile.TemporaryDirectory(prefix="rp_cex_") as td:
        tmp = Path(td)
        prep_il(leaf, net, tmp)
        gold_mod = json.loads((tmp / "gold.json").read_text(encoding="utf-8"))["modules"]["gold"]
        gate_mod = json.loads((tmp / "gate.json").read_text(encoding="utf-8"))["modules"]["gate"]
        gmap, gamb = group_by_key(extract_flops(gold_mod))
        tmap, tamb = group_by_key(extract_flops(gate_mod))
        if gamb or tamb:
            print(f"CEX FAIL ambiguous gold={gamb} gate={tamb}")
            return
        keys = sorted(set(gmap) & set(tmap))
        gold_only = sorted(set(gmap) - set(tmap))
        gate_only = sorted(set(tmap) - set(gmap))
        print(f"CEX pairs={len(keys)} keys={' '.join(keys) or '-'}")
        print(f"CEX unmatched gold={gold_only or '-'} gate={gate_only or '-'}")
        # Analysis only: unique same-width leftovers (crc_word vs word_q).
        used_g, used_t = set(keys), set(keys)
        for gk in gold_only:
            cands = [tk for tk in gate_only if tk not in used_t and tmap[tk].width == gmap[gk].width]
            if len(cands) == 1:
                alias = f"{gk}__{cands[0]}"
                gmap[alias] = gmap[gk]
                tmap[alias] = tmap[cands[0]]
                keys.append(alias)
                used_g.add(gk)
                used_t.add(cands[0])
                print(f"CEX width_alias gold={gk} gate={cands[0]} width={gmap[gk].width}")
        keys = sorted(set(keys))
        pairs_g = [(k, gmap[k]) for k in keys]
        pairs_t = [(k, tmap[k]) for k in keys]
        write_cut_script(
            tmp / "cut_gold.ys", "gold", pairs_g, tmp / "gold.il",
            tmp / "gold_cut.il", tmp / "gold_cut.json",
            strip_ports_for([gmap[k] for k in keys], gold_mod),
        )
        write_cut_script(
            tmp / "cut_gate.ys", "gate", pairs_t, tmp / "gate.il",
            tmp / "gate_cut.il", tmp / "gate_cut.json",
            strip_ports_for([tmap[k] for k in keys], gate_mod),
        )
        gcut = run_yosys_file(tmp / "cut_gold.ys", 60)
        tcut = run_yosys_file(tmp / "cut_gate.ys", 60)
        if gcut.returncode != 0 or tcut.returncode != 0:
            print((gcut.stdout or "") + (tcut.stdout or ""))
            return

        gold_ports = json.loads((tmp / "gold_cut.json").read_text(encoding="utf-8"))["modules"]["gold"]["ports"]
        show = [
            n for n in (
                "rp_d_crc", "rp_d_crc_word", "rp_d_word", "rp_d_done",
                "crc_word", "done", "ok", "error_flag",
            )
            if n in gold_ports
        ]
        vectors = [
            ("gap_after_reset", {"rst_pyc": 0, "rp_q_crc": INIT, "start": 0, "valid_in": 0, "last": 0, "data_in": 0}),
            ("mid_last_from_init", {"rst_pyc": 0, "rp_q_crc": INIT, "start": 0, "valid_in": 1, "last": 1, "data_in": 0}),
            ("mid_continue", {"rst_pyc": 0, "rp_q_crc": INIT, "start": 0, "valid_in": 1, "last": 0, "data_in": 0}),
            ("idle_leftover_q", {"rst_pyc": 0, "rp_q_crc": 0x155, "start": 0, "valid_in": 0, "last": 0, "data_in": 0}),
            ("start_only", {"rst_pyc": 0, "rp_q_crc": 0x155, "start": 1, "valid_in": 0, "last": 0, "data_in": 0}),
            ("xia_start_valid_last", {"rst_pyc": 0, "rp_q_crc": INIT, "start": 1, "valid_in": 1, "last": 1, "data_in": 0}),
        ]
        for qn in ("rp_q_crc_word", "rp_q_word", "rp_q_done", "rp_q_ok", "rp_q_recv"):
            if qn.replace("rp_q_", "") in keys or qn[5:] in keys:
                for _name, assigns in vectors:
                    assigns.setdefault(qn, 0)

        first_diff = None
        for name, assigns in vectors:
            # Only set signals that exist as cut PIs.
            use = {k: v for k, v in assigns.items() if k in gold_ports}
            gvals = eval_signals(tmp / "gold_cut.il", "gold", use, [s for s in show if True])
            tvals = eval_signals(tmp / "gate_cut.il", "gate", use, [s for s in show if True])
            q_crc = use.get("rp_q_crc", INIT)
            start, valid, last = use.get("start", 0), use.get("valid_in", 0), use.get("last", 0)
            gd, td = gvals.get("rp_d_crc"), tvals.get("rp_d_crc")
            differ = gd is not None and td is not None and gd != td
            print(
                f"CEX vec={name} class={classify(start, valid, last)} "
                f"reachable={reachable_from_reset(q_crc, start, valid, last)} "
                f"Q_crc=0x{q_crc:x} start={start} valid_in={valid} last={last} "
                f"gold_D_crc={gd} gate_D_crc={td} "
                f"gold_D_word={gvals.get('rp_d_crc_word', gvals.get('rp_d_word'))} "
                f"gate_D_word={tvals.get('rp_d_crc_word', tvals.get('rp_d_word'))} "
                f"differ={differ}"
            )
            if differ and first_diff is None:
                first_diff = name

        # Isolated SAT on rp_d_crc if present.
        gold_po = [
            n for n, info in json.loads((tmp / "gold_cut.json").read_text(encoding="utf-8"))["modules"]["gold"]["ports"].items()
            if info.get("direction") == "output"
        ]
        target = "rp_d_crc" if "rp_d_crc" in gold_po else next((n for n in gold_po if n.startswith("rp_d_crc")), None)
        if not target:
            print("CEX sat=skipped (no rp_d_crc PO)")
            print(f"CEX first_diff_vec={first_diff}")
            return
        others = [n for n in gold_po if n != target]
        drop = "\n".join(f"delete -output {n}" for n in others)
        sat_ys = (
            f"read_rtlil {tmp / 'gold_cut.il'}\ncd gold\n{drop}\nwrite_rtlil {tmp / 'g1.il'}\n"
            "design -reset\n"
            f"read_rtlil {tmp / 'gate_cut.il'}\ncd gate\n{drop}\nwrite_rtlil {tmp / 't1.il'}\n"
            "design -reset\n"
            f"read_rtlil {tmp / 'g1.il'}\nread_rtlil {tmp / 't1.il'}\n"
            "miter -equiv -flatten -make_assert gold gate wit\n"
            "hierarchy -top wit\n"
            "sat -verify -prove-asserts -show-inputs -timeout 45\n"
        )
        sat = run_yosys_p(sat_ys, 50)
        kind = sat_kind(sat.stdout or "")
        print(f"CEX sat_po={target} kind={kind}")
        for line in (sat.stdout or "").splitlines():
            if any(k in line for k in ("SAT", "Assert", "Eval", "rp_q_", "start", "valid", "last", "trigger")):
                print(f"CEX sat_line={line.strip()}")
        print(f"CEX first_diff_vec={first_diff}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-design", action="store_true")
    ap.add_argument("--leaf")
    ap.add_argument("--net")
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    if args.all_design:
        cases = [
            ("ub_dll_bcrc", "TX-PRODUCT", ROOT / "rtl/dll/ub_dll_bcrc.v"),
            ("ub_dll_bcrc", "TX-HOOKS", ROOT / "rtl/dll/hooks/ub_dll_bcrc.v"),
            ("ub_dll_bcrc_check", "RX-PRODUCT", ROOT / "rtl/dll/ub_dll_bcrc_check.v"),
            ("ub_dll_bcrc_check", "RX-HOOKS", ROOT / "rtl/dll/hooks/ub_dll_bcrc_check.v"),
        ]
        for leaf, label, net in cases:
            if net.is_file():
                dump_one(leaf, label, net)
            else:
                print(f"CEX SKIP {label} missing {net}")
        return 0
    if not args.leaf or not args.net:
        raise SystemExit("need --all-design or --leaf + --net")
    dump_one(args.leaf, args.label or args.leaf, Path(args.net))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
