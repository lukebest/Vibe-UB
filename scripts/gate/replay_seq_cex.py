#!/usr/bin/env python3
"""Replay a BCRC seq CEX on Icarus: gold ref, DUT net, tb/models.

Prints the first beat/port that differs. Exit 1 when gold and gate ports
differ (expected for a fake / real #5 CEX). Exit 0 if they match.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tb.models.ub_dll_bcrc import UbDllBcrc, pack_bcrc_word  # noqa: E402

TB_TX = """`timescale 1ns/1ps
module replay;
  reg core_clk, rst_pyc, start, valid_in, last;
  reg [159:0] data_in;
  wire [31:0] crc_word;
  wire done;
  ub_dll_bcrc dut (
    .core_clk(core_clk), .rst_pyc(rst_pyc), .start(start),
    .valid_in(valid_in), .data_in(data_in), .last(last),
    .crc_word(crc_word), .done(done)
  );
  initial core_clk = 0;
  always #5 core_clk = ~core_clk;
  initial begin
    rst_pyc = 0; start = 0; valid_in = 0; last = 0; data_in = 0;
    {STIM}
    $finish;
  end
endmodule
"""

TB_RX = """`timescale 1ns/1ps
module replay;
  reg core_clk, rst_pyc, start, valid_in, last;
  reg [159:0] data_in;
  reg [31:0] crc_recv;
  wire [31:0] crc_word;
  wire done, crc_ok, crc_fail, error_flag_rx;
  ub_dll_bcrc_check dut (
    .core_clk(core_clk), .rst_pyc(rst_pyc), .start(start),
    .valid_in(valid_in), .data_in(data_in), .last(last),
    .crc_recv(crc_recv), .crc_word(crc_word), .done(done),
    .crc_ok(crc_ok), .crc_fail(crc_fail), .error_flag_rx(error_flag_rx)
  );
  initial core_clk = 0;
  always #5 core_clk = ~core_clk;
  initial begin
    rst_pyc = 0; start = 0; valid_in = 0; last = 0; data_in = 0; crc_recv = 0;
    {STIM}
    $finish;
  end
endmodule
"""


def parse_int(raw: str) -> int:
    s = (raw or "0").strip()
    if not s:
        return 0
    if s.startswith(("0x", "0X")):
        return int(s, 16)
    if "'" in s:
        body = s.split("'", 1)[1]
        if body[:1] in "hH":
            return int(body[1:] or "0", 16)
        if body[:1] in "bB":
            return int(body[1:] or "0", 2)
        return int(body or "0", 2)
    try:
        return int(s, 10)
    except ValueError:
        return int(s, 16)


def beat_tx(rst: int, start: int, valid: int, last: int, data: int) -> str:
    return (
        f"    rst_pyc={rst}; start={start}; valid_in={valid}; last={last}; "
        f"data_in=160'h{data:040x};\n"
        "    @(posedge core_clk); #1;\n"
        '    $display("REPLAY rst=%b start=%b valid=%b last=%b data=%h '
        'crc_word=%h done=%b", rst_pyc, start, valid_in, last, data_in, '
        "crc_word, done);\n"
    )


def beat_rx(rst: int, start: int, valid: int, last: int, data: int, recv: int) -> str:
    return (
        f"    rst_pyc={rst}; start={start}; valid_in={valid}; last={last}; "
        f"data_in=160'h{data:040x}; crc_recv=32'h{recv:08x};\n"
        "    @(posedge core_clk); #1;\n"
        '    $display("REPLAY rst=%b start=%b valid=%b last=%b data=%h '
        'recv=%h crc_word=%h done=%b crc_ok=%b crc_fail=%b error_flag_rx=%b", '
        "rst_pyc, start, valid_in, last, data_in, crc_recv, crc_word, done, "
        "crc_ok, crc_fail, error_flag_rx);\n"
    )


def compile_run(tb: Path, srcs: list[Path], inc: list[Path]) -> tuple[int, str]:
    out = tb.parent / "sim.vvp"
    cmd = ["iverilog", "-g2012", "-o", str(out)]
    for d in inc:
        if d.is_dir():
            cmd.append(f"-I{d}")
    cmd.append(str(tb))
    cmd.extend(str(s) for s in srcs)
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    run = subprocess.run(["vvp", str(out)], text=True, capture_output=True, check=False)
    return run.returncode, (run.stdout or "") + (run.stderr or "")


def parse_replay(log: str) -> list[dict[str, str]]:
    rows = []
    for line in log.splitlines():
        if not line.startswith("REPLAY "):
            continue
        rec = {}
        for tok in line.split()[1:]:
            if "=" in tok:
                k, v = tok.split("=", 1)
                rec[k] = v
        if rec:
            rows.append(rec)
    return rows


def model_rows(stim: list[tuple[int, int, int, int, int]]) -> list[dict[str, str]]:
    model = UbDllBcrc()
    out = []
    for rst, start, valid, last, data in stim:
        if rst:
            model.reset()
            word, done = 0, 0
        else:
            if start:
                model.start()
            done = 0
            word = 0
            if valid:
                crc = model.eat(data, last=bool(last))
                if crc is not None:
                    word = pack_bcrc_word(crc, 0, 0)
                    done = 1
                    model.reset()
        out.append({"crc_word": f"{word:08x}", "done": str(done)})
    return out


def first_diff(
    gold: list[dict[str, str]],
    gate: list[dict[str, str]],
    ports: tuple[str, ...],
) -> tuple[int, str, str, str] | None:
    n = min(len(gold), len(gate))
    for i in range(n):
        for p in ports:
            gv, tv = gold[i].get(p, ""), gate[i].get(p, "")
            if gv == "" or tv == "":
                continue
            try:
                if parse_int(gv) != parse_int(tv):
                    return i + 1, p, gv, tv
            except ValueError:
                if gv.lower() != tv.lower():
                    return i + 1, p, gv, tv
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--net", required=True, type=Path)
    ap.add_argument("--leaf", default="ub_dll_bcrc")
    ap.add_argument("--gold", action="append", default=[])
    args = ap.parse_args()
    leaf = args.leaf
    rx = leaf == "ub_dll_bcrc_check"
    golds = [Path(p) for p in args.gold] or (
        [ROOT / "formal/dll/ref/ub_dll_bcrc.sv", ROOT / "formal/dll/ref/ub_dll_bcrc_check.sv"]
        if rx
        else [ROOT / "formal/dll/ref/ub_dll_bcrc.sv"]
    )
    rows = list(csv.DictReader(args.csv.open(encoding="utf-8")))
    if not rows:
        print("REPLAY FAIL empty csv")
        return 2
    stim_tx: list[tuple[int, int, int, int, int]] = []
    stim_rx: list[int] = []
    for r in rows:
        stim_tx.append(
            (
                parse_int(r.get("rst_pyc", "0")),
                parse_int(r.get("start", "0")),
                parse_int(r.get("valid_in", "0")),
                parse_int(r.get("last", "0")),
                parse_int(r.get("data_in", "0")),
            )
        )
        stim_rx.append(parse_int(r.get("crc_recv", "0")) if rx else 0)
    if rx:
        body = "".join(beat_rx(*tx, recv) for tx, recv in zip(stim_tx, stim_rx))
        tb_src = TB_RX.replace("{STIM}", body)
        ports = ("crc_word", "done", "crc_ok", "crc_fail", "error_flag_rx")
    else:
        body = "".join(beat_tx(*tx) for tx in stim_tx)
        tb_src = TB_TX.replace("{STIM}", body)
        ports = ("crc_word", "done")
    inc = [ROOT / "rtl/pyc_lib", ROOT / "rtl/common", args.net.parent]
    with tempfile.TemporaryDirectory(prefix="replay_") as td:
        td_p = Path(td)
        gold_tb = td_p / "gold.sv"
        gate_tb = td_p / "gate.sv"
        gold_tb.write_text(tb_src, encoding="utf-8")
        gate_tb.write_text(tb_src, encoding="utf-8")
        grc, glog = compile_run(gold_tb, golds, inc)
        trc, tlog = compile_run(gate_tb, [args.net], inc)
        print("=== Icarus gold ===")
        print(glog)
        print("=== Icarus gate ===")
        print(tlog)
        if grc != 0 or trc != 0:
            print("REPLAY FAIL compile/run")
            return 2
        grows = parse_replay(glog)
        trows = parse_replay(tlog)
        mrows = model_rows(stim_tx)
        print("=== tb/models ===")
        for i, rec in enumerate(mrows, 1):
            rst, start, valid, last, data = stim_tx[i - 1]
            print(
                f"MODEL t={i} rst={rst} start={start} valid={valid} last={last} "
                f"data=0x{data:x} crc_word={rec['crc_word']} done={rec['done']}"
            )
        diff = first_diff(grows, trows, ports)
        if diff:
            beat_i, port, gv, tv = diff
            print(f"REPLAY FIRST_DIFF beat={beat_i} port={port} gold={gv} gate={tv}")
            md = first_diff(grows, mrows, ("crc_word", "done"))
            if md:
                print(f"REPLAY gold_vs_model beat={md[0]} port={md[1]} gold={md[2]} model={md[3]}")
            else:
                print("REPLAY gold_vs_model=match")
            return 1
        print("REPLAY gold_vs_gate=match (seq CEX did not reproduce on Icarus ports)")
        md = first_diff(grows, mrows, ("crc_word", "done"))
        if md:
            print(f"REPLAY gold_vs_model beat={md[0]} port={md[1]} gold={md[2]} model={md[3]}")
        else:
            print("REPLAY gold_vs_model=match")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
