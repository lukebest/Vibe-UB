#!/usr/bin/env python3
"""Impl quick-synth driver: Yosys flatten + Sky130 hd map + OpenSTA setup path.

Informational only. Never a merge gate. See docs/rules/impl_quick_synth.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DEFAULT = SCRIPT_DIR.parents[1]

# SPEC §4.1 / §9: F_CORE = 2.578125e9 / 32 ≈ 80.57 MHz
SPEC_LINE_RATE_GBPS = 2.578125
SPEC_PMA_W = 32
SPEC_F_CORE_HZ = SPEC_LINE_RATE_GBPS * 1e9 / SPEC_PMA_W
SPEC_PERIOD_NS = 1e9 / SPEC_F_CORE_HZ  # 12.412121... ns
PLACEHOLDER_PERIOD_NS = 2.0  # 500 MHz, only if SPEC states no frequency

# OPEN §13 elab tokens from pycircuit/lib/elab_open.py (not product defaults).
# taps=23'h2, init=23'h5, seed slot k = k+3. Forbidden: tap 17 / seed 2'b01.
_SCR_W = 23
_SEED_SLOTS = 9


def _elab_seed_map(scr_w: int = _SCR_W, slots: int = _SEED_SLOTS) -> int:
    acc = 0
    for lid in range(slots):
        acc |= (lid + 3) << (scr_w * lid)
    return acc


ELAB_SEED_MAP = _elab_seed_map()
ELAB_SEED_MAP_W = _SCR_W * _SEED_SLOTS

# Known OPEN / draft parameters. Applied only via Yosys chparam (command line).
PLACEHOLDER_PARAMS: dict[str, dict[str, Any]] = {
    "ub_pcs_scrambler": {
        "chparam": {
            "SCR_TAPS": f"{_SCR_W}'h2",
            "LFSR_INIT": f"{_SCR_W}'h5",
            "SEED_MAP": f"{ELAB_SEED_MAP_W}'h{ELAB_SEED_MAP:x}",
        },
        "label": (
            "placeholder chparam OPEN §13 elab tokens "
            "(SCR_TAPS=23'h2, LFSR_INIT=23'h5, SEED_MAP slot k=k+3); "
            "not product defaults; PRBS23 taps/seed pending §13"
        ),
    },
    "ub_pcs_descrambler": {
        "chparam": {
            "SCR_TAPS": f"{_SCR_W}'h2",
            "LFSR_INIT": f"{_SCR_W}'h5",
            "SEED_MAP": f"{ELAB_SEED_MAP_W}'h{ELAB_SEED_MAP:x}",
        },
        "label": (
            "placeholder chparam OPEN §13 elab tokens "
            "(SCR_TAPS=23'h2, LFSR_INIT=23'h5, SEED_MAP slot k=k+3); "
            "not product defaults; PRBS23 taps/seed pending §13"
        ),
    },
    "ub_dll_retry_req_sm": {
        "chparam": {
            "NUM_RETRY_THRESHOLD": "15",
            "NUM_PHY_REINIT_THRESHOLD": "4",
            "RETRY_WAIT_CYC": "323",
        },
        "label": (
            "placeholder chparam draft §13 / SPEC §9 "
            "(NUM_RETRY_THRESHOLD=15, NUM_PHY_REINIT_THRESHOLD=4, "
            "RETRY_WAIT_CYC=323); not closed product defaults"
        ),
    },
}

LANE_LEAF_TOPS = ("ub_pcs_lane_dist", "ub_pcs_lane_dedist")

DFF_CELL_RE = re.compile(
    r"sky130_fd_sc_hd__(?:edf|sdf|df)[a-z0-9_]*", re.IGNORECASE
)
LATCH_CELL_RE = re.compile(r"(?:dlatch|sky130_fd_sc_hd__dlxt)", re.IGNORECASE)
CELL_COUNT_RE = re.compile(r"Number of cells:\s+(\d+)")
AREA_RE = re.compile(r"Chip area for module '\\?\$?[^']*':\s+([0-9.]+)")
AREA_RE_ALT = re.compile(r"Chip area for top module.*:\s+([0-9.]+)")
LTP_LEN_RE = re.compile(
    r"Longest topological path:\s+(\d+)|ltp\s*=\s*(\d+)|path length\s+(\d+)",
    re.IGNORECASE,
)


def die(msg: str, code: int = 2) -> None:
    print(f"quick_synth: {msg}", file=sys.stderr)
    raise SystemExit(code)


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )


def git(repo: Path, *args: str) -> str:
    cp = run(["git", *args], cwd=repo)
    if cp.returncode != 0:
        die(f"git {' '.join(args)} failed:\n{cp.stdout}")
    return cp.stdout


def resolve_ref(repo: Path, ref: str) -> str:
    return git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").strip()


def detect_period(spec_text: str | None) -> tuple[float, str, bool]:
    """Return (period_ns, source_label, is_placeholder)."""
    if not spec_text:
        return (
            PLACEHOLDER_PERIOD_NS,
            "placeholder 500 MHz (2.0 ns); SPEC.md not found",
            True,
        )
    if re.search(
        r"2\.578125\s*(?:e9|G|Gb)|80\.57\s*MHz|F_CORE", spec_text, re.IGNORECASE
    ):
        return (
            SPEC_PERIOD_NS,
            (
                "SPEC.md §4.1 / §9 F_CORE = 2.578125e9/32 ≈ 80.57 MHz "
                f"→ period {SPEC_PERIOD_NS:.9f} ns"
            ),
            False,
        )
    return (
        PLACEHOLDER_PERIOD_NS,
        "placeholder 500 MHz (2.0 ns); SPEC.md states no target frequency",
        True,
    )


_PORT_RE = re.compile(
    r"(?P<dir>input|output|inout)\s+(?:wire|reg|logic)?\s*(?:\[[^\]]+\])?\s*(?P<name>\w+)",
)


def list_ports(verilog: str) -> list[tuple[str, str]]:
    # Only the module header — do not pick up function/task ports.
    m = re.search(
        r"module\s+\w+\s*(?:#\s*\([^;]*?\))?\s*\((.*?)\);",
        verilog,
        re.S,
    )
    blob = m.group(1) if m else verilog
    if not re.search(r"\b(input|output|inout)\b", blob) and m:
        rest = verilog[m.end() :]
        cut = re.search(r"\b(always|assign|function|task|generate)\b", rest)
        blob = rest[: cut.start()] if cut else rest
    return [(p.group("dir"), p.group("name")) for p in _PORT_RE.finditer(blob)]


def find_clock_port(verilog: str) -> str | None:
    names = [n for _d, n in list_ports(verilog)]
    for cand in ("core_clk", "clk"):
        if cand in names:
            return cand
    for n in names:
        if re.search(r"clk", n, re.IGNORECASE):
            return n
    return None


def find_includes(src: Path, tree: Path) -> list[Path]:
    text = src.read_text(encoding="utf-8", errors="replace")
    out: list[Path] = []
    for inc in re.findall(r'`include\s+"([^"]+)"', text):
        for base in (src.parent, tree / "rtl" / "common", tree / "rtl"):
            cand = (base / inc).resolve()
            if cand.is_file() and cand not in out:
                out.append(cand)
                break
    return out


def list_rtl_leaves(tree: Path) -> dict[str, dict[str, Path]]:
    """Map module name -> {product, hooks?} for rtl/**/*.v,*.sv (not hooks as product)."""
    found: dict[str, dict[str, Path]] = {}
    rtl = tree / "rtl"
    if not rtl.is_dir():
        return found
    for path in sorted(rtl.rglob("*")):
        if path.suffix not in {".v", ".sv"}:
            continue
        if path.name.endswith(".vh"):
            continue
        name = path.stem
        rec = found.setdefault(name, {})
        parts = path.relative_to(rtl).parts
        if "hooks" in parts:
            rec["hooks"] = path
        else:
            rec["product"] = path
    return found


def default_tops(repo: Path, tree: Path, base: str, head: str | None) -> list[str]:
    if head is None:
        # Working tree vs base.
        cp = run(
            [
                "git",
                "diff",
                "--name-only",
                "--diff-filter=ACMR",
                base,
                "--",
                "rtl/",
            ],
            cwd=repo,
        )
        names = cp.stdout.splitlines()
    else:
        cp = run(
            [
                "git",
                "diff",
                "--name-only",
                "--diff-filter=ACMR",
                base,
                head,
                "--",
                "rtl/",
            ],
            cwd=repo,
        )
        names = cp.stdout.splitlines()
    tops: list[str] = []
    for rel in names:
        p = Path(rel)
        if p.suffix not in {".v", ".sv"}:
            continue
        if "hooks" in p.parts:
            continue
        if not str(p).startswith("rtl/"):
            continue
        # Design leaves are ub_*; skip library cells such as pyc_reg.
        if not p.stem.startswith("ub_"):
            continue
        tops.append(p.stem)
    # unique, stable
    seen: set[str] = set()
    out: list[str] = []
    for t in tops:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def parse_stat(text: str) -> dict[str, Any]:
    cells = None
    m = CELL_COUNT_RE.search(text)
    if m:
        cells = int(m.group(1))
    area = None
    ma = AREA_RE.search(text) or AREA_RE_ALT.search(text)
    if ma:
        area = float(ma.group(1))
    flops = 0
    for line in text.splitlines():
        if DFF_CELL_RE.search(line):
            nm = re.search(r"\s(\d+)\s*$", line)
            # yosys stat: "    sky130_fd_sc_hd__dfxtp_1     12"
            parts = line.strip().split()
            if parts and parts[-1].isdigit() and "sky130" in parts[0]:
                if DFF_CELL_RE.search(parts[0]):
                    flops += int(parts[-1])
    latches = 0
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1].isdigit() and LATCH_CELL_RE.search(parts[0]):
            latches += int(parts[-1])
    return {
        "cells": cells,
        "area_um2": area,
        "flops": flops,
        "latches_from_stat": latches,
        "raw": text,
    }


def parse_ltp(text: str) -> int | None:
    # Yosys 0.33 ltp prints something like:
    # "Longest topological path: foo -> ... (length = N)"
    for rx in (
        re.compile(r"length\s*=\s*(\d+)", re.IGNORECASE),
        re.compile(r"Longest topological path:\s+(\d+)"),
        re.compile(r"\bltp\b.*?(\d+)"),
    ):
        m = rx.search(text)
        if m:
            return int(m.group(1))
    # Fallback: count " -> " hops on the last path-looking line.
    for line in reversed(text.splitlines()):
        if "->" in line:
            return line.count("->")
    return None


def parse_scc(text: str) -> int:
    m = re.search(r"Found\s+(\d+)\s+logic\s+loop", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    if re.search(r"Found logic loop", text, re.IGNORECASE):
        return 1
    return 0


def parse_select_list(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("Warning") or s.startswith("End of"):
            continue
        if re.match(r"^(Executing|Finished|yosys|--)", s, re.IGNORECASE):
            continue
        items.append(s)
    return items


_SEQ_CELL_RE = re.compile(
    r"sky130_fd_sc_hd__(?:edf|sdf|df)[a-z0-9_]+", re.IGNORECASE
)


def _parse_sta_block(block: str) -> dict[str, Any] | None:
    if "data arrival time" not in block:
        return None
    group_m = re.search(r"Path Group:\s+(\S+)", block)
    group = group_m.group(1) if group_m else ""
    arrivals = re.findall(r"(-?[0-9.]+)\s+data arrival time", block)
    slacks = re.findall(r"(-?[0-9.]+)\s+slack\s+\((MET|VIOLATED)\)", block)
    if not arrivals and not slacks:
        return None
    arrival = float(arrivals[0]) if arrivals else None
    slack = float(slacks[0][0]) if slacks else None
    data = block.split("data arrival time")[0]
    combo: list[str] = []
    for line in data.splitlines():
        m = re.search(r"\((sky130_fd_sc_hd__[A-Za-z0-9_]+)\)", line)
        if not m:
            continue
        cell = m.group(1)
        if _SEQ_CELL_RE.search(cell):
            continue
        pin = re.search(r"\s([A-Za-z_][A-Za-z0-9_./]*)/", line)
        key = pin.group(1) if pin else cell
        if key not in combo:
            combo.append(key)
    return {
        "group": group,
        "arrival_ns": arrival,
        "slack_ns": slack,
        "logic_depth": len(combo),
        "path_cells": combo,
    }


def parse_sta(text: str) -> dict[str, Any]:
    if "Startpoint" in text:
        parts = ["Startpoint" + p for p in text.split("Startpoint")[1:]]
    else:
        parts = [text]
    blocks = [b for b in (_parse_sta_block(p) for p in parts) if b]
    chosen = None
    clk_blocks = [b for b in blocks if b["group"] == "core_clk"]
    pool = clk_blocks or [b for b in blocks if "async" not in (b["group"] or "")]
    if not pool:
        pool = blocks
    if pool:
        chosen = min(
            pool,
            key=lambda b: b["slack_ns"] if b["slack_ns"] is not None else 1e9,
        )
    if chosen is None:
        return {
            "arrival_ns": None,
            "slack_ns": None,
            "logic_depth": None,
            "path_cells": [],
            "raw": text,
        }
    return {**chosen, "raw": text}


def tool_versions(liberty: Path, liberty_meta: dict[str, str]) -> dict[str, str]:
    y = run(["yosys", "-V"])
    yver = (y.stdout or "").strip().splitlines()[0] if y.stdout else "unknown"
    sta = run(["sta", "-no_init", "-exit"])
    sta_ver = "unknown"
    for line in (sta.stdout or "").splitlines():
        if "OpenSTA" in line:
            sta_ver = line.strip()
            break
    return {
        "yosys": yver,
        "opensta": sta_ver,
        "liberty_path": str(liberty),
        **liberty_meta,
    }


def extract_tree(repo: Path, ref: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "archive", "--format=tar", ref],
        cwd=repo,
        stdout=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        die(f"git archive {ref} failed")
    tar = subprocess.run(
        ["tar", "-x", "-C", str(dest)],
        input=proc.stdout,
        check=False,
    )
    if tar.returncode != 0:
        die(f"tar extract of {ref} failed")


def synthesize_one(
    *,
    top: str,
    src: Path,
    tree: Path,
    outdir: Path,
    liberty: Path,
    chparam: dict[str, str] | None,
    extra_chparam: dict[str, str] | None,
    period_ns: float,
    variant: str,
) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    files = [src]
    for inc in find_includes(src, tree):
        if inc not in files:
            files.append(inc)

    text = src.read_text(encoding="utf-8", errors="replace")
    clk = find_clock_port(text)
    ports = list_ports(text)
    in_ports = [n for d, n in ports if d in ("input", "inout") and n != clk]
    out_ports = [n for d, n in ports if d in ("output", "inout")]

    merged: dict[str, str] = {}
    notes: list[str] = []
    if top in PLACEHOLDER_PARAMS:
        merged.update(PLACEHOLDER_PARAMS[top]["chparam"])
        notes.append(PLACEHOLDER_PARAMS[top]["label"])
    if chparam:
        merged.update(chparam)
    if extra_chparam:
        merged.update(extra_chparam)

    ch_cmd = ""
    if merged:
        parts = [f"-set {k} {v}" for k, v in merged.items()]
        ch_cmd = "chparam " + " ".join(parts) + f" {top}"

    env = os.environ.copy()
    env["QS_TOP"] = top
    env["QS_FILES"] = " ".join(str(p) for p in files)
    env["QS_LIBERTY"] = str(liberty)
    env["QS_OUTDIR"] = str(outdir)
    env["QS_CHPARAM"] = ch_cmd
    env["QS_READ_SV"] = "1" if src.suffix == ".sv" or any(
        p.suffix == ".sv" for p in files
    ) else "0"

    yosys_log = outdir / "yosys.log"
    ycmd = ["yosys", "-c", str(SCRIPT_DIR / "quick_synth.tcl")]
    y = run(ycmd, cwd=tree, env=env, timeout=900)
    yosys_log.write_text(y.stdout or "", encoding="utf-8")

    result: dict[str, Any] = {
        "top": top,
        "variant": variant,
        "src": str(src.relative_to(tree)) if src.is_relative_to(tree) else str(src),
        "clock_port": clk,
        "chparam": merged,
        "notes": notes,
        "yosys_rc": y.returncode,
        "ok": y.returncode == 0,
    }
    if y.returncode != 0:
        result["error"] = "yosys failed"
        result["log_excerpt"] = _excerpt(y.stdout or "")
        result["anomalies"] = ["yosys_failed"]
        return result

    designer = parse_stat((outdir / "designer_stat.txt").read_text(errors="replace"))
    generic = parse_stat(
        (outdir / "generic_synth_stat.txt").read_text(errors="replace")
    )
    mapped = parse_stat((outdir / "mapped_stat.txt").read_text(errors="replace"))
    if mapped["cells"] == 0 and mapped["area_um2"] is None:
        mapped["area_um2"] = 0.0
    ltp = parse_ltp((outdir / "ltp.txt").read_text(errors="replace"))
    loops = parse_scc((outdir / "scc_synth.txt").read_text(errors="replace"))
    loops += parse_scc((outdir / "scc_proc.txt").read_text(errors="replace"))
    latch_sel = parse_select_list(
        (outdir / "latch_generic.txt").read_text(errors="replace")
    )
    mem_sel = parse_select_list((outdir / "mem_generic.txt").read_text(errors="replace"))

    result.update(
        {
            "cells_proc_opt": designer["cells"],
            "cells_generic_synth": generic["cells"],
            "cells_mapped": mapped["cells"],
            "area_um2": mapped["area_um2"],
            "flops": mapped["flops"],
            "ltp": ltp,
            "comb_loops": loops,
            "latches_generic": latch_sel,
            "mem_generic": mem_sel,
        }
    )

    # STA
    mapped_v = outdir / "mapped.v"
    env["QS_NETLIST"] = str(mapped_v)
    env["QS_PERIOD_NS"] = f"{period_ns:.9f}"
    env["QS_CLK_PORT"] = clk or ""
    env["QS_CLK_NAME"] = "core_clk"
    env["QS_INPUTS"] = " ".join(in_ports)
    env["QS_OUTPUTS"] = " ".join(out_ports)
    sta_log = outdir / "sta.log"
    s = run(
        ["sta", "-no_init", "-exit", str(SCRIPT_DIR / "sta.tcl")],
        cwd=tree,
        env=env,
        timeout=300,
    )
    sta_log.write_text(s.stdout or "", encoding="utf-8")
    result["sta_rc"] = s.returncode
    setup_rpt = outdir / "sta_worst_setup.rpt"
    unc_rpt = outdir / "sta_unconstrained.rpt"
    sta_parsed = {"arrival_ns": None, "slack_ns": None, "logic_depth": None}
    if setup_rpt.is_file():
        sta_parsed = parse_sta(setup_rpt.read_text(errors="replace"))
    if sta_parsed.get("arrival_ns") is None and unc_rpt.is_file():
        unc = parse_sta(unc_rpt.read_text(errors="replace"))
        if unc.get("arrival_ns") is not None:
            sta_parsed = unc
            notes.append("STA used unconstrained combo path (no sequential endpoint)")
    if s.returncode != 0 and sta_parsed.get("arrival_ns") is None:
        result["sta_error"] = "opensta failed"
        result["sta_log_excerpt"] = _excerpt(s.stdout or "")
        notes.append("opensta failed; see sta.log")
    result["arrival_ns"] = sta_parsed.get("arrival_ns")
    result["slack_ns"] = sta_parsed.get("slack_ns")
    result["logic_depth"] = sta_parsed.get("logic_depth")
    if clk is None:
        notes.append("no clock port; virtual core_clk used for I/O delay")
    elif clk != "core_clk":
        notes.append(f"clock port '{clk}' mapped to SDC clock core_clk")

    anomalies = detect_anomalies(result, text, y.stdout or "")
    result["anomalies"] = anomalies
    result["notes"] = notes
    return result


def detect_anomalies(r: dict[str, Any], src_text: str, yosys_log: str) -> list[str]:
    a: list[str] = []
    if r.get("latches_generic"):
        a.append("latch_inferred: " + ", ".join(r["latches_generic"][:8]))
    if r.get("mem_generic"):
        a.append("inferred_memory: " + ", ".join(r["mem_generic"][:8]))
    if r.get("comb_loops"):
        a.append(f"comb_loop_count={r['comb_loops']}")
    slack = r.get("slack_ns")
    if slack is not None and slack < 0:
        a.append(f"setup_violation slack={slack} ns")
    cells = r.get("cells_mapped")
    area = r.get("area_um2")
    flops = r.get("flops") or 0
    proc_cells = r.get("cells_proc_opt")
    sequential_src = bool(re.search(r"always\s+@\s*\(\s*posedge", src_text))
    # Pure wiring (bit permute) maps to 0 std cells; that is not a sweep-away.
    wiring_only = (
        cells == 0
        and (proc_cells in (0, None))
        and not sequential_src
    )
    if wiring_only:
        r.setdefault("notes", []).append(
            "combinational wiring only (0 std cells after map; bit permute / assign)"
        )
    elif cells == 0:
        a.append("near_zero_cells_after_map (module optimized away)")
    elif sequential_src and flops == 0 and cells is not None and cells <= 2:
        a.append("near_zero_cells_after_map (possible unused/undriven sweep)")
    if area is not None and area > 20000:
        a.append(f"unexpectedly_large_area {area:.1f} um^2")
    if cells is not None and cells > 8000:
        a.append(f"unexpectedly_large_cell_count {cells}")
    if re.search(r"removing unused", yosys_log, re.IGNORECASE):
        if cells == 0:
            a.append("yosys_removed_unused_logic")
    return a


def _excerpt(text: str, n: int = 40) -> str:
    lines = text.strip().splitlines()
    if len(lines) <= n:
        return text.strip()
    return "\n".join(lines[-n:])


def fmt_num(v: Any, digits: int = 3) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return str(v)


def write_markdown_table(rows: list[dict[str, Any]]) -> str:
    hdr = (
        "| module | variant | cells (mapped) | area um^2 | flops | "
        "logic depth | arrival ns | slack @ period | delta vs main | notes |"
    )
    sep = "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |"
    lines = [hdr, sep]
    for r in rows:
        notes = "; ".join(r.get("notes") or [])
        an = r.get("anomalies") or []
        if an:
            notes = (("ANOMALY: " + "; ".join(an) + ". ") + notes).strip()
        if r.get("error"):
            notes = f"FAIL: {r['error']}. " + notes
        delta = r.get("delta_vs_main") or "new"
        lines.append(
            "| {mod} | {var} | {cells} | {area} | {flops} | {depth} | {arr} | {sl} | {delta} | {notes} |".format(
                mod=r.get("top", ""),
                var=r.get("variant", ""),
                cells=fmt_num(r.get("cells_mapped"), 0),
                area=fmt_num(r.get("area_um2"), 1),
                flops=fmt_num(r.get("flops"), 0),
                depth=fmt_num(r.get("logic_depth"), 0),
                arr=fmt_num(r.get("arrival_ns"), 3),
                sl=fmt_num(r.get("slack_ns"), 3),
                delta=delta,
                notes=notes.replace("|", "/") or "—",
            )
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Impl quick-synth (Sky130 hd tt proxy)")
    ap.add_argument("--repo", type=Path, default=REPO_DEFAULT)
    ap.add_argument("--ref", help="git ref to synthesize (archive to a temp tree)")
    ap.add_argument("--work-tree", type=Path, help="existing tree (skip git archive)")
    ap.add_argument("--base", default="origin/main", help="diff base for default tops")
    ap.add_argument("--tops", help="comma-separated top module names")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--liberty", type=Path, default=None)
    ap.add_argument(
        "--extra-num-lanes",
        default="8",
        help="also elaborate lane dist/dedist at this NUM_LANES (empty to skip)",
    )
    ap.add_argument(
        "--json",
        type=Path,
        help="write machine-readable results (default: <out>/results.json)",
    )
    args = ap.parse_args(argv)

    repo = args.repo.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    liberty = args.liberty or Path(os.environ.get("SKY130_HD_LIB", ""))
    if not liberty or not Path(liberty).is_file():
        die("SKY130_HD_LIB not set or file missing")
    liberty = Path(liberty).resolve()

    liberty_meta = {
        "liberty_source": os.environ.get("SKY130_HD_LIB_SOURCE", "env:SKY130_HD_LIB"),
        "liberty_commit": os.environ.get("SKY130_HD_LIB_COMMIT", "unknown"),
    }

    cleanup: Path | None = None
    head_sha = None
    if args.work_tree:
        tree = args.work_tree.resolve()
        if args.ref:
            head_sha = resolve_ref(repo, args.ref)
        else:
            head_sha = git(repo, "rev-parse", "HEAD").strip()
    elif args.ref:
        head_sha = resolve_ref(repo, args.ref)
        cleanup = Path(tempfile.mkdtemp(prefix="quick_synth_"))
        extract_tree(repo, head_sha, cleanup)
        tree = cleanup
    else:
        tree = repo
        head_sha = git(repo, "rev-parse", "HEAD").strip()

    try:
        spec_path = tree / "docs" / "SPEC.md"
        spec_text = spec_path.read_text(encoding="utf-8") if spec_path.is_file() else None
        period_ns, period_src, period_ph = detect_period(spec_text)

        leaves = list_rtl_leaves(tree)
        if args.tops:
            tops = [t.strip() for t in args.tops.split(",") if t.strip()]
        else:
            tops = default_tops(repo, tree, args.base, args.ref or head_sha)
        if not tops:
            die("no tops to synthesize (pass --tops or touch rtl/ leaves)")

        versions = tool_versions(liberty, liberty_meta)
        jobs: list[tuple[str, str, Path, dict[str, str] | None]] = []
        for top in tops:
            rec = leaves.get(top)
            if not rec or "product" not in rec:
                # still record a skip
                jobs.append((top, "PRODUCT", Path(), None))
                continue
            jobs.append((top, "PRODUCT", rec["product"], None))
            if "hooks" in rec:
                jobs.append((top, "HOOKS", rec["hooks"], None))
            if top in LANE_LEAF_TOPS and args.extra_num_lanes:
                jobs.append(
                    (
                        top,
                        f"PRODUCT_NUM_LANES={args.extra_num_lanes}",
                        rec["product"],
                        {"NUM_LANES": args.extra_num_lanes},
                    )
                )

        results: list[dict[str, Any]] = []
        for top, variant, src, extra in jobs:
            if not src:
                results.append(
                    {
                        "top": top,
                        "variant": variant,
                        "ok": False,
                        "error": "skipped: rtl file not found in this tree",
                        "notes": ["module of this name is not in the extracted tree"],
                        "anomalies": [],
                    }
                )
                continue
            run_dir = out / f"{top}__{variant.replace('=', '_')}"
            print(f"==> {top} {variant}  src={src}", flush=True)
            r = synthesize_one(
                top=top,
                src=src,
                tree=tree,
                outdir=run_dir,
                liberty=liberty,
                chparam=None,
                extra_chparam=extra,
                period_ns=period_ns,
                variant=variant,
            )
            results.append(r)

        payload = {
            "head_sha": head_sha,
            "base": args.base,
            "period_ns": period_ns,
            "period_source": period_src,
            "period_placeholder": period_ph,
            "tools": versions,
            "results": results,
        }
        jpath = args.json or (out / "results.json")
        jpath.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(write_markdown_table(results))
        print(f"\nJSON: {jpath}")
        return 0 if all(r.get("ok") for r in results) else 1
    finally:
        if cleanup is not None:
            shutil.rmtree(cleanup, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
