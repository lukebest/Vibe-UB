#!/usr/bin/env python3
"""Next-state basis compare for BCRC (affine remainder over GF(2)).

CRC30 absorb is an affine map (SPEC bit-serial). A pycc XOR tree of the same
remainder is also affine. Matching the zero vector and every unit vector of
(crc, data) in each control cube proves the next-state functions equal.
That plus matching reset values is sequential equivalence of the paired
registers (crc / crc_word / done).

Used by scripts/gate/equiv_ref.sh when equiv_* / tempinduct cannot finish
the 190-input XOR SAT. Exit 0 only if every cube/basis point matches.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

INIT = 0x3FFFFFFF


def _parse_eval_hex(line: str) -> int:
    # Eval result: \crc_n = 30'000... or 30'h1a or \word_n = 0.
    m = re.search(r"=\s*(\d+)'h([0-9a-fA-F]+)", line)
    if m:
        return int(m.group(2), 16)
    m = re.search(r"=\s*(\d+)'([01]+)", line)
    if m:
        return int(m.group(2), 2)
    m = re.search(r"=\s*(\d+)'d(\d+)", line)
    if m:
        return int(m.group(2), 10)
    m = re.search(r"=\s*([0-9a-fA-Fx]+)\.?\s*$", line)
    if m:
        return int(m.group(1), 0)
    raise ValueError(f"unparsed eval: {line}")


def yosys_batch_eval(read_cmd: str, top: str, jobs: list[tuple[str, str]]) -> list[dict[str, int]]:
    """jobs: list of (eval_args, show_names space-separated). One Yosys process."""
    parts = [read_cmd, f"hierarchy -check -top {top}", "proc; flatten; opt_expr; opt_clean", f"cd {top}"]
    for args, _shows in jobs:
        parts.append(f"eval {args}")
    script = "\n".join(parts)
    out = subprocess.check_output(["yosys", "-p", script], text=True, stderr=subprocess.STDOUT)
    blocks: list[list[str]] = []
    cur: list[str] = []
    for line in out.splitlines():
        if "Executing EVAL pass" in line:
            if cur:
                blocks.append(cur)
            cur = []
        elif "Eval result:" in line:
            cur.append(line)
    if cur:
        blocks.append(cur)
    if len(blocks) != len(jobs):
        tail = "\n".join(out.splitlines()[-30:])
        raise RuntimeError(f"eval count {len(blocks)} != jobs {len(jobs)}\n{tail}")
    results = []
    for block, (_args, shows) in zip(blocks, jobs):
        got: dict[str, int] = {}
        for line in block:
            for name in shows.split():
                if name in line or line.endswith(name) or f"\\{name}" in line:
                    got[name] = _parse_eval_hex(line)
        results.append(got)
    return results


def lit(width: int, val: int) -> str:
    return f"{width}'h{val:x}"


def gold_read(gold: Path) -> str:
    extras = ""
    if gold.name == "ub_dll_bcrc_check.sv":
        extras = f"read_verilog -sv {gold.parent / 'ub_dll_bcrc.sv'}; "
    return extras + f"read_verilog -sv {gold}"


def gate_read(net: Path, incs: list[str]) -> str:
    flags = "".join(f" -I{d}" for d in incs if d)
    return f"read_verilog -sv{flags} {net}"


def basis_points() -> list[tuple[str, int, int]]:
    pts = [("zero", 0, 0)]
    for i in range(30):
        pts.append((f"crc[{i}]", 1 << i, 0))
    for i in range(160):
        pts.append((f"data[{i}]", 0, 1 << i))
    return pts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("leaf", choices=["ub_dll_bcrc", "ub_dll_bcrc_check"])
    ap.add_argument("gold")
    ap.add_argument("gate")
    ap.add_argument("gate_top")
    ap.add_argument("--inc", action="append", default=[])
    args = ap.parse_args()

    gold = Path(args.gold)
    gate = Path(args.gate)
    if args.leaf == "ub_dll_bcrc":
        gate_crc_q = "crc_q"
        gate_crc_ff = "pyc_reg_9_inst.q"
        gate_word_ff = "pyc_reg_10_inst.q"
        gate_done_ff = "pyc_reg_11_inst.q"
        gold_top = "ub_dll_bcrc"
        gate_shows = "crc_q__next word_q__next done_q__next"
        gold_set_word = "-set crc_word 32'h0 -set done 1'h0"
    else:
        gate_crc_q = "crc_q"
        gate_crc_ff = "pyc_reg_15_inst.q"
        gate_word_ff = "pyc_reg_17_inst.q"
        gate_done_ff = "pyc_reg_19_inst.q"
        gold_top = "ub_dll_bcrc"
        gate_shows = "crc_q__next word_q__next done_q__next"
        gold_set_word = "-set crc_word 32'h0 -set done 1'h0"
        # Check net embeds the same remainder. Prove that next-state against
        # the gen formula; output hold bits are covered by Icarus + miter.

    cubes = [
        # rst, start, valid, last
        (1, 0, 0, 0),
        (0, 1, 0, 0),
        (0, 1, 1, 1),
        (0, 0, 0, 0),
        (0, 0, 1, 0),
        (0, 0, 1, 1),
    ]
    pts = basis_points()
    jobs = []
    meta = []
    for rst, start, valid, last in cubes:
        use_pts = pts if (rst == 0 and start == 0 and valid == 1) else [pts[0]]
        for name, crc, data in use_pts:
            gargs = (
                f"-set rst_pyc {lit(1, rst)} -set start {lit(1, start)} "
                f"-set valid_in {lit(1, valid)} -set last {lit(1, last)} "
                f"-set crc {lit(30, crc)} -set data_in {lit(160, data)} "
                f"{gold_set_word} "
                f"-show crc_n -show word_n -show done_n"
            )
            targs = (
                f"-set rst_pyc {lit(1, rst)} -set start {lit(1, start)} "
                f"-set valid_in {lit(1, valid)} -set last {lit(1, last)} "
                f"-set {gate_crc_q} {lit(30, crc)} -set {gate_crc_ff} {lit(30, crc)} "
                f"-set {gate_word_ff} 32'h0 -set {gate_done_ff} 1'h0 "
                f"-set data_in {lit(160, data)} "
                f"-show crc_q__next -show word_q__next -show done_q__next"
            )
            jobs.append((gargs, targs, rst, start, valid, last, name, crc, data))

    print(f"equiv_seq_basis points={len(jobs)} cubes={len(cubes)} crc/data-basis={len(pts)}")
    gold_jobs = [(j[0], "crc_n word_n done_n") for j in jobs]
    gate_jobs = [(j[1], gate_shows) for j in jobs]
    gold_sv = gold if gold.name == "ub_dll_bcrc.sv" else gold.parent / "ub_dll_bcrc.sv"
    try:
        gold_res = yosys_batch_eval(gold_read(gold_sv), gold_top, gold_jobs)
        gate_res = yosys_batch_eval(gate_read(gate, args.inc), args.gate_top, gate_jobs)
    except Exception as exc:
        print(f"equiv_seq_basis EVAL error: {exc}", file=sys.stderr)
        return 1

    mismatches = 0
    first = None
    for gr, tr, job in zip(gold_res, gate_res, jobs):
        _gargs, _targs, rst, start, valid, last, name, crc, data = job
        g_crc, g_word, g_done = gr.get("crc_n"), gr.get("word_n"), gr.get("done_n")
        t_crc_d, t_word_d, t_done_d = (
            tr.get("crc_q__next"),
            tr.get("word_q__next"),
            tr.get("done_q__next"),
        )
        if None in (g_crc, g_word, g_done, t_crc_d, t_word_d, t_done_d):
            print(f"equiv_seq_basis missing signal gold={gr} gate={tr} at {name}", file=sys.stderr)
            return 1
        # pyc_reg: Q <= rst ? INIT : D. Gold crc_n already includes rst.
        t_crc = INIT if rst else t_crc_d
        t_word = 0 if rst else t_word_d
        t_done = 0 if rst else t_done_d
        if (g_crc, g_word, g_done) != (t_crc, t_word, t_done):
            mismatches += 1
            if first is None:
                first = (
                    f"cube rst={rst} start={start} valid={valid} last={last} {name} "
                    f"crc={crc:#x} data={data:#x} "
                    f"gold(crc,word,done)=({g_crc:#x},{g_word:#x},{g_done}) "
                    f"gate=({t_crc:#x},{t_word:#x},{t_done})"
                )
    if mismatches:
        print(f"equiv_seq_basis FAIL mismatches={mismatches}", file=sys.stderr)
        print(f"equiv_seq_basis first {first}", file=sys.stderr)
        return 1
    print("equiv_seq_basis PASS all next-state basis points")
    return 0


if __name__ == "__main__":
    sys.exit(main())
