#!/usr/bin/env python3
"""Uncut output-only sequential compare for scripts/gate/equiv_ref.sh.

Each side starts at its own reset value (eval D under rst_pyc=1; setattr
init on Q). Never pass -set-init-zero (that forces crc=0, not INIT) or
-set-init-def (Yosys 0.33 satgen.h:91).

CEX search: write_aiger -zinit (no -miter: that would treat gold.done=1
as a bad state), then ABC bmc3. Timeout is neither pass nor disprove.
Yosys sat dumps the input sequence when a CEX exists (rst held 2 cycles
at steps 1-2, -prove-skip 2 so asserts fire only after release).
Induction (tempinduct / ABC pdr,dprove) must converge to pass.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

FF_TYPES = {
    "$dff",
    "$dffe",
    "$ff",
    "$sdff",
    "$sdffe",
    "$sdffce",
    "$adff",
    "$adffe",
}

RST_HOLD_STEPS = 2


def yosys_id(name: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    return "\\" + name + " "


def run(cmd: list[str], tmo: int) -> subprocess.CompletedProcess[str]:
    argv = ["timeout", str(tmo), *cmd] if tmo > 0 else cmd
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def yosys(script: str, tmo: int) -> subprocess.CompletedProcess[str]:
    return run(["yosys", "-p", script], tmo)


def net_of(mod: dict, bits: list) -> str | None:
    target = tuple(bits or [])
    if not target:
        return None
    scored: list[tuple[int, int, int, str]] = []
    for name, info in (mod.get("netnames") or {}).items():
        if tuple(info.get("bits") or []) != target:
            continue
        hide = 1 if info.get("hide_name") else 0
        ugly = 1 if ("$" in name or "func" in name) else 0
        scored.append((hide, ugly, len(name), name))
    if not scored:
        return None
    scored.sort()
    return scored[0][3]


def parse_width(raw: object, fallback: int) -> int:
    s = str(raw or "").strip()
    if re.fullmatch(r"[01]+", s) and len(s) > 2:
        return int(s, 2)
    if s:
        try:
            return int(s, 0)
        except ValueError:
            pass
    return fallback


def parse_eval_values(text: str) -> dict[str, int]:
    got: dict[str, int] = {}
    for line in text.splitlines():
        if "Eval result:" not in line:
            continue
        m = re.search(r"Eval result:\s*\\?(\S+)\s*=\s*(.+?)\s*$", line)
        if not m:
            continue
        name, raw = m.group(1), m.group(2).strip().rstrip(".")
        val: int | None = None
        if re.fullmatch(r"\d+'h[0-9a-fA-F]+", raw):
            val = int(raw.split("'h", 1)[1], 16)
        elif re.fullmatch(r"\d+'b[01]+", raw):
            val = int(raw.split("'b", 1)[1], 2)
        elif re.fullmatch(r"\d+'[01]+", raw):
            val = int(raw.split("'", 1)[1], 2)
        elif re.fullmatch(r"-?\d+", raw):
            val = int(raw, 10)
        if val is not None:
            got[name] = val
    return got


def flatten_side(
    reads: list[str],
    top: str,
    name: str,
    tmp: Path,
    chparam: str,
    tmo: int,
) -> tuple[Path, Path]:
    js, il = tmp / f"{name}.json", tmp / f"{name}.il"
    body = "\n".join(reads)
    extra = f"{chparam}\n" if chparam else ""
    proc = yosys(
        f"{body}\nhierarchy -check -top {top}\n{extra}rename -top {name}\n"
        f"proc; flatten; opt_expr; opt_clean\nwrite_json {js}\nwrite_rtlil {il}\n",
        tmo,
    )
    if proc.returncode != 0 or not js.is_file():
        print(proc.stdout or "")
        raise SystemExit(f"seq flatten failed side={name} rc={proc.returncode}")
    return js, il


def _q_reset_fallback(qn: str, width: int) -> int:
    last = qn.replace("/", ".").split(".")[-1].lower()
    last = re.sub(r"\[[^\]]+\]$", "", last)
    if last in {"crc", "crc_q"} or last.endswith(".crc"):
        return (1 << width) - 1 if width >= 30 else (1 << width) - 1
    return 0


def apply_reset_init(il: Path, js: Path, top: str, rst: str, tmo: int) -> dict[str, int]:
    """Set each FF Q init to D evaluated under reset (sync rst_pyc)."""
    mod = json.loads(js.read_text(encoding="utf-8"))["modules"][top]
    pairs: list[tuple[str, str, int]] = []
    for _cname, cell in (mod.get("cells") or {}).items():
        if (cell.get("type") or "") not in FF_TYPES:
            continue
        conns = cell.get("connections") or {}
        qn = net_of(mod, conns.get("Q") or conns.get("q") or [])
        dn = net_of(mod, conns.get("D") or conns.get("d") or [])
        w = parse_width((cell.get("parameters") or {}).get("WIDTH"), len(conns.get("Q") or []) or 1)
        if qn and dn:
            pairs.append((qn, dn, w))
    if not pairs:
        print(f"equiv_ref SEQ init side={top} flops=0")
        return {}
    # Ugly $0\\crc_word[31:0] D nets: alias to seqd_N so eval -show is reliable.
    alias_lines = [f"read_rtlil {il}", f"cd {top}"]
    alias_of: dict[str, str] = {}
    for i, (qn, dn, w) in enumerate(pairs):
        alias = f"seqd_{i}"
        alias_lines += [
            f"add -wire {alias} {w}",
            f"connect -set {alias} {yosys_id(dn)}",
        ]
        alias_of[qn] = alias
    alias_il = il.with_suffix(".alias.il")
    alias_lines.append(f"write_rtlil {alias_il}")
    al = yosys("\n".join(alias_lines) + "\n", tmo)
    if al.returncode != 0:
        print(al.stdout or "")
        alias_il = il
        alias_of = {qn: dn for qn, dn, _w in pairs}
    shows = " ".join(f"-show {yosys_id(a)}" for a in alias_of.values())
    ev = yosys(f"read_rtlil {alias_il}\ncd {top}\neval -set {rst} 1 {shows}\n", tmo)
    vals = parse_eval_values(ev.stdout or "")
    lines = [f"read_rtlil {il}", f"cd {top}"]
    qinit: dict[str, int] = {}
    for qn, dn, w in pairs:
        alias = alias_of.get(qn, dn)
        raw = vals.get(alias)
        if raw is None:
            raw = vals.get(alias.lstrip("\\"))
        if raw is None:
            raw = _q_reset_fallback(qn, w)
            print(f"equiv_ref SEQ init_fallback side={top} q={qn} d={dn} val=0x{raw:x}")
        lines.append(f"setattr -set init {w}'h{raw:x} {yosys_id(qn)}")
        qinit[qn] = raw
        print(f"equiv_ref SEQ init side={top} q={qn} d={dn} val=0x{raw:x} w={w}")
    lines.append(f"write_rtlil {il}")
    wr = yosys("\n".join(lines) + "\n", tmo)
    if wr.returncode != 0:
        print(wr.stdout or "")
        raise SystemExit(f"seq setattr init failed side={top}")
    print(f"equiv_ref SEQ init side={top} flops={len(qinit)}")
    return qinit


def write_miter_aig(gold_il: Path, gate_il: Path, aig: Path, tmo: int) -> str:
    # -make_assert → $assert (outputs differ). write_aiger maps $assert to
    # AIGER bad states. Do NOT pass -miter: that would treat gold.done=1
    # itself as a CEX.
    proc = yosys(
        f"""
read_rtlil {gold_il}
read_rtlil {gate_il}
miter -equiv -flatten -make_assert gold gate miter
hierarchy -top miter
opt_expr; opt_clean
delete t:$assume t:$live t:$fair
techmap; opt; dffunmap; aigmap; opt
write_aiger -symbols -zinit {aig}
""",
        tmo,
    )
    print(proc.stdout or "")
    return proc.stdout or ""


def abc_bmc3(aig: Path, abc: str, frames: int, tmo: int, cex: Path) -> tuple[str, int | None]:
    cmd = f"read {aig}; bmc3 -F {frames} -T {tmo} -v; write_cex -n {cex}"
    print(f"equiv_ref SEQ abc_bmc3={cmd}")
    proc = run([abc, "-c", cmd], tmo + 5)
    log = proc.stdout or ""
    print(log)
    frame = None
    m = re.search(r"was asserted in frame\s+(\d+)", log, re.I)
    if m:
        frame = int(m.group(1))
    return log, frame


def parse_abc_named_cex(path: Path) -> list[dict[str, str]]:
    """Parse `write_cex -n` (`name@frame=bit`)."""
    if not path.is_file():
        return []
    bits: dict[int, dict[str, int]] = {}
    buses: dict[int, dict[str, dict[int, int]]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"([A-Za-z0-9_./]+)(?:\[(\d+)\])?@(\d+)=([01])", line)
        if not m:
            continue
        name, idx, frame_s, bit = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        rec = bits.setdefault(frame_s, {})
        bus = buses.setdefault(frame_s, {})
        if idx is None:
            rec[name] = bit
        else:
            bus.setdefault(name, {})[int(idx)] = bit
    if not bits and not buses:
        return []
    frames = sorted(set(bits) | set(buses))
    steps: list[dict[str, str]] = []
    for fr in frames:
        rec: dict[str, str] = {"_step": str(fr + 1)}
        for name, val in (bits.get(fr) or {}).items():
            rec[name] = str(val)
        for name, idxmap in (buses.get(fr) or {}).items():
            width = max(idxmap) + 1
            acc = 0
            for i, b in idxmap.items():
                acc |= (b & 1) << i
            rec[name] = f"0x{acc:x}" if width > 1 else str(acc)
        steps.append(rec)
    return steps


def abc_kind(log: str) -> str:
    if re.search(r"Networks are equivalent", log):
        return "equivalent"
    if re.search(r"was asserted in frame|NOT EQUIVALENT|Verification failed", log, re.I):
        return "not_equivalent"
    if re.search(r"time ?out|timed out|undecided|UNDECIDED|No output asserted", log, re.I):
        return "unproven"
    return "unproven"


def parse_sat_steps(log: str) -> list[dict[str, str]]:
    """Parse Yosys sat model table (Time / Signal / Dec / Hex / Bin)."""
    by_step: dict[int, dict[str, str]] = {}
    in_table = False
    for line in log.splitlines():
        if re.search(r"Time Signal Name", line):
            in_table = True
            continue
        if not in_table:
            if re.search(r"Time step|Sat timestep|Step \d", line, re.I):
                m = re.search(r"(\d+)", line)
                step_i = int(m.group(1)) if m else 0
                by_step.setdefault(step_i, {})["_step"] = str(step_i)
            m = re.search(r"^\s*(\\?[A-Za-z0-9_./\[\]]+)\s*=\s*(.+?)\s*$", line)
            if m:
                step_i = max(by_step) if by_step else 0
                by_step.setdefault(step_i, {})[m.group(1).lstrip("\\")] = m.group(2).strip().rstrip(".")
            continue
        if re.match(r"^\s*-{4,}", line):
            continue
        m = re.match(
            r"^\s+(init|\d+)\s+\\?(\S+)\s+(\S+)\s+(\S+)\s+([01 -]+)\s*$",
            line,
        )
        if not m:
            continue
        step_s, name, _dec, hx, bn = m.groups()
        step_i = 0 if step_s == "init" else int(step_s)
        rec = by_step.setdefault(step_i, {})
        rec["_step"] = str(step_i)
        bits = bn.replace(" ", "")
        if hx not in {"--", "-"} and re.fullmatch(r"[0-9a-fA-F]+", hx):
            rec[name] = f"0x{hx}" if len(hx) > 1 else hx
        elif re.fullmatch(r"[01]+", bits):
            rec[name] = f"0x{int(bits, 2):x}" if len(bits) > 1 else bits
    return [by_step[k] for k in sorted(by_step)]


def _hex_or_int(raw: str) -> str:
    s = raw.strip().rstrip(".")
    if re.fullmatch(r"\d+'h[0-9a-fA-F]+", s):
        w, h = s.split("'h", 1)
        return f"0x{h}" if int(w) > 1 else str(int(h, 16))
    if re.fullmatch(r"\d+'b[01]+", s):
        w, b = s.split("'b", 1)
        v = int(b, 2)
        return f"0x{v:x}" if int(w) > 1 else str(v)
    if re.fullmatch(r"\d+'[01]+", s):
        w, b = s.split("'", 1)
        v = int(b, 2)
        return f"0x{v:x}" if int(w) > 1 else str(v)
    if re.fullmatch(r"[01]+", s) and len(s) > 1:
        return f"0x{int(s, 2):x}"
    return s


def interesting_ports() -> tuple[str, ...]:
    return (
        "rst_pyc",
        "start",
        "valid_in",
        "last",
        "data_in",
        "crc_recv",
        "crc_word",
        "done",
        "crc_ok",
        "crc_fail",
        "error_flag_rx",
        "trigger",
    )


def _row_rst(st: dict[str, str]) -> int:
    for cand in ("in_rst_pyc", "rst_pyc"):
        if cand in st and st[cand] not in {"", "0x", "0x0"}:
            try:
                return int(st[cand], 0) if str(st[cand]).startswith("0") else int(st[cand])
            except ValueError:
                return 1 if st[cand] not in {"0", "0x0"} else 0
    return 0


def write_cex_csv(steps: list[dict[str, str]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # BMC starts at reset values. Icarus regs do not: prefix two rst=1 beats
    # so the dumped sequence is a self-contained port stimulus.
    if steps and _row_rst(steps[0]) == 0:
        idle = {"_step": "0", "in_rst_pyc": "1", "rst_pyc": "1", "in_start": "0",
                "in_valid_in": "0", "in_last": "0", "in_data_in": "0x0"}
        steps = [{**idle, "_step": "pre1"}, {**idle, "_step": "pre2"}, *steps]
    keys = ["step", "rst_pyc", "start", "valid_in", "last", "data_in", "crc_recv"]
    out_keys = [
        "gold_crc_word",
        "gate_crc_word",
        "gold_done",
        "gate_done",
        "gold_crc_ok",
        "gate_crc_ok",
        "gold_crc_fail",
        "gate_crc_fail",
        "gold_error_flag_rx",
        "gate_error_flag_rx",
    ]
    rows = []
    for st in steps:
        row = {"step": st.get("_step", "")}
        for k in keys[1:]:
            val = ""
            for cand in (f"in_{k}", k, f"gold_{k}", f"gate_{k}"):
                if cand in st:
                    val = _hex_or_int(st[cand])
                    break
            row[k] = val
        for k in ("crc_word", "done", "crc_ok", "crc_fail", "error_flag_rx"):
            g = st.get(f"gold_{k}") or st.get(f"gold.{k}") or ""
            t = st.get(f"gate_{k}") or st.get(f"gate.{k}") or ""
            # miter may use gold_gold_* after flatten
            if not g:
                for name, val in st.items():
                    if name.endswith(k) and "gold" in name.lower():
                        g = val
                        break
            if not t:
                for name, val in st.items():
                    if name.endswith(k) and "gate" in name.lower():
                        t = val
                        break
            row[f"gold_{k}"] = _hex_or_int(g) if g else ""
            row[f"gate_{k}"] = _hex_or_int(t) if t else ""
        rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys + out_keys)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print(f"equiv_ref SEQ cex_csv={path}")
    for row in rows:
        print("equiv_ref SEQ cex_row " + " ".join(f"{k}={row[k]}" for k in keys + out_keys if row.get(k) != ""))
    return path


def sat_dump(
    gold_il: Path,
    gate_il: Path,
    tmp: Path,
    depth: int,
    tmo: int,
    hold_rst: bool,
    leaf: str = "ub_dll_bcrc",
) -> tuple[str, list[dict[str, str]]]:
    rst = ""
    skip = ""
    if hold_rst:
        rst = " ".join(f"-set-at {i} in_rst_pyc 1" for i in range(1, RST_HOLD_STEPS + 1))
        skip = f"-prove-skip {RST_HOLD_STEPS}"
    vcd = tmp / "cex.vcd"
    shows = "-show-inputs -show-outputs -show-regs -show gold.crc_word -show gate.crc_word -show gold.done -show gate.done"
    if leaf == "ub_dll_bcrc_check":
        shows += (
            " -show gold.crc_ok -show gate.crc_ok -show gold.crc_fail -show gate.crc_fail "
            "-show gold.error_flag_rx -show gate.error_flag_rx"
        )
    sat = (
        f"sat -seq {depth} -verify -prove-asserts {skip} {rst} "
        f"{shows} -dump_vcd {vcd} -timeout {tmo}"
    )
    print(f"equiv_ref SEQ sat={sat}")
    proc = yosys(
        f"""
read_rtlil {gold_il}
read_rtlil {gate_il}
miter -equiv -flatten -make_assert gold gate miter
hierarchy -top miter
opt_expr; opt_clean
{sat}
""",
        tmo + 10,
    )
    log = proc.stdout or ""
    print(log)
    return log, parse_sat_steps(log)


def sat_kind(log: str) -> str:
    if re.search(r"time ?out|timed out", log, re.I):
        return "unproven"
    if re.search(r"SAT [Mm]odel|Assert failed|failed to prove|proof did fail|SATISFIABLE", log, re.I):
        return "not_equivalent"
    if re.search(r"proved|UNSAT|verified successfully|successful proof", log, re.I):
        return "equivalent"
    return "unproven"


def gold_reads(root: Path, leaf: str, inc: list[str]) -> list[str]:
    flags = " ".join(f"-I{d}" for d in inc)
    if leaf == "ub_dll_bcrc_check":
        return [
            f"read_verilog -sv {flags} {root / 'formal/dll/ref/ub_dll_bcrc.sv'}",
            f"read_verilog -sv {flags} {root / 'formal/dll/ref/ub_dll_bcrc_check.sv'}",
        ]
    if leaf == "ub_dll_bcrc":
        return [f"read_verilog -sv {flags} {root / 'formal/dll/ref/ub_dll_bcrc.sv'}"]
    if leaf == "ub_pyc_rst_adapt":
        return [f"read_verilog -sv {flags} {root / 'formal/common/ref/ub_pyc_rst_adapt.sv'}"]
    layer = "pcs" if "lane" in leaf else "dll"
    extra = []
    if leaf == "ub_pcs_lane_collect":
        extra = [
            f"read_verilog -sv {flags} {root / 'formal/pcs/ref/ub_pcs_lane_dist.sv'}",
            f"read_verilog -sv {flags} {root / 'formal/pcs/ref/ub_pcs_lane_dedist.sv'}",
        ]
    return extra + [f"read_verilog -sv {flags} {root / f'formal/{layer}/ref/{leaf}.sv'}"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--leaf", required=True)
    ap.add_argument("--net", required=True, type=Path)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--tmp", type=Path, required=True)
    ap.add_argument("--abc", default="yosys-abc")
    ap.add_argument("--tmo", type=int, default=40)
    ap.add_argument("--depth", type=int, default=8)
    ap.add_argument("--inc", action="append", default=[])
    ap.add_argument("--gold-chparam", default="")
    ap.add_argument("--gate-chparam", default="")
    ap.add_argument("--gate-top", default="")
    ap.add_argument("--cex-dir", type=Path, default=None)
    args = ap.parse_args()
    tmp = args.tmp
    tmp.mkdir(parents=True, exist_ok=True)
    net = args.net.resolve()
    leaf = args.leaf
    gate_top = args.gate_top or leaf
    inc = [str(Path(p)) for p in args.inc]
    flags = " ".join(f"-I{d}" for d in inc)

    print(f"equiv_ref SEQ leaf={leaf} net={net} depth={args.depth} tmo={args.tmo}")
    print("equiv_ref SEQ forbid=-set-init-zero -set-init-def")
    print("equiv_ref SEQ init=reset-value (eval D under rst_pyc=1; write_aiger -zinit)")
    print(f"equiv_ref SEQ rst_hold=steps 1..{RST_HOLD_STEPS} prove-skip={RST_HOLD_STEPS}")
    print("equiv_ref SEQ abc_bmc3=read miter.aig; bmc3 -F {0} -T {1} -v".format(max(args.depth, 16), args.tmo))

    greads = gold_reads(args.root, leaf, inc)
    gjs, gil = flatten_side(greads, leaf, "gold", tmp, args.gold_chparam, args.tmo)
    treads = [f"read_verilog -sv {flags} {net}"]
    tjs, til = flatten_side(treads, gate_top, "gate", tmp, args.gate_chparam, args.tmo)
    apply_reset_init(gil, gjs, "gold", "rst_pyc", args.tmo)
    apply_reset_init(til, tjs, "gate", "rst_pyc", args.tmo)

    aig = tmp / "miter.aig"
    write_miter_aig(gil, til, aig, args.tmo)
    if not aig.is_file() or aig.stat().st_size == 0:
        print("equiv_ref SEQ bmc3=unproven (empty aiger)")
        return 2

    named_cex = tmp / "bmc3.cex"
    bmc_log, frame = abc_bmc3(aig, args.abc, max(args.depth, 16), args.tmo, named_cex)
    kind = abc_kind(bmc_log)
    if frame is not None or kind == "not_equivalent":
        print(f"equiv_ref SEQ bmc3=CEX frame={frame}")
        steps = parse_abc_named_cex(named_cex)
        if not steps:
            dump_depth = max(args.depth, (frame or 0) + RST_HOLD_STEPS + 2)
            slog, steps = sat_dump(gil, til, tmp, dump_depth, args.tmo, hold_rst=False, leaf=leaf)
            if sat_kind(slog) != "not_equivalent":
                slog, steps = sat_dump(gil, til, tmp, dump_depth, args.tmo, hold_rst=True, leaf=leaf)
        label = net.stem
        cex_dir = args.cex_dir or tmp
        csv_path = cex_dir / f"{label}.csv"
        if steps:
            write_cex_csv(steps, csv_path)
        else:
            print("equiv_ref SEQ cex_csv=missing (bmc3 CEX, no named cex / sat model)")
        print("equiv_ref SEQ result=not_equivalent method=abc-bmc3")
        return 1
    if re.search(r"time ?out|timed out", bmc_log, re.I) or kind == "unproven":
        print("equiv_ref SEQ bmc3=timeout/undecided (not a pass, not a CEX)")

    slog, steps = sat_dump(gil, til, tmp, args.depth, args.tmo, hold_rst=True, leaf=leaf)
    sk = sat_kind(slog)
    if sk == "not_equivalent":
        label = net.stem
        cex_dir = args.cex_dir or tmp
        if steps:
            write_cex_csv(steps, cex_dir / f"{label}.csv")
        print("equiv_ref SEQ result=not_equivalent method=sat-bmc")
        return 1

    induct = yosys(
        f"""
read_rtlil {gil}
read_rtlil {til}
miter -equiv -flatten -make_assert gold gate miter
hierarchy -top miter
opt
sat -verify -tempinduct -prove-asserts -prove-skip {RST_HOLD_STEPS} """
        + " ".join(f"-set-at {i} in_rst_pyc 1" for i in range(1, RST_HOLD_STEPS + 1))
        + f" -timeout {args.tmo}\n",
        args.tmo + 10,
    )
    ilog = induct.stdout or ""
    print(ilog)
    ik = sat_kind(ilog)
    if ik == "equivalent":
        print("equiv_ref SEQ result=equivalent method=sat-tempinduct")
        return 0
    if ik == "not_equivalent":
        print("equiv_ref SEQ result=not_equivalent method=sat-tempinduct")
        return 1

    abc = args.abc
    for cmd in ("pdr", "dprove"):
        clog = run([abc, "-c", f"read {aig}; {cmd}"], args.tmo + 5).stdout or ""
        print(f"equiv_ref SEQ abc_cmd=read {aig}; {cmd}")
        print(clog)
        ck = abc_kind(clog)
        if ck == "equivalent":
            print(f"equiv_ref SEQ result=equivalent method=abc-{cmd}")
            return 0
        if ck == "not_equivalent":
            print(f"equiv_ref SEQ result=not_equivalent method=abc-{cmd}")
            return 1

    print(f"equiv_ref SEQ 未证完 (BMC {args.depth} cycles, induction did not converge)")
    print("equiv_ref SEQ result=unproven")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
