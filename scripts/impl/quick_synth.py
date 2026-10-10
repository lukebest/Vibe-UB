#!/usr/bin/env python3
"""Impl quick-synth driver: Yosys flatten + Sky130 hd map + OpenSTA setup path.

Informational only. Never a merge gate. See docs/rules/impl_quick_synth.md.

SPEC §2.2: each file under rtl/<block>/*.v is one top (no required chparam).
HOOKS live in rtl/<block>/hooks/ with the same name. `_placeholder` variants
are lint/TB only. Large ub_cmn_mem_1r1w instances are blackboxed.
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

from buffer_fanout import (
    DEFAULT_MAX_FANOUT,
    analyze_design,
    buffer_design,
    buffer_module,
    choose_buf,
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DEFAULT = SCRIPT_DIR.parents[1]

# SPEC §4.1 / §9: F_CORE = 2.578125e9 / 32 ≈ 80.57 MHz
SPEC_LINE_RATE_GBPS = 2.578125
SPEC_PMA_W = 32
SPEC_F_CORE_HZ = SPEC_LINE_RATE_GBPS * 1e9 / SPEC_PMA_W
SPEC_PERIOD_NS = 1e9 / SPEC_F_CORE_HZ  # 12.412121... ns
PLACEHOLDER_PERIOD_NS = 2.0  # 500 MHz, only if SPEC states no frequency

# SPEC §2.2: pycc emits no Verilog parameter; each parameter set is a
# fixed netlist named <leaf>_<tag>. Placeholder tags are lint/TB only.
PLACEHOLDER_TAG = "_placeholder"
QOR_DELTA_THRESHOLD = 0.10  # flag |Δ| / |baseline| > 10%
QOR_COMPARE_FIELDS = ("cells_mapped", "area_um2", "logic_depth", "slack_ns")
QOR_FIELD_SHORT = {
    "cells_mapped": "cells",
    "area_um2": "area",
    "logic_depth": "depth",
    "slack_ns": "slack",
}

MEM_PRIMITIVE_PREFIX = "ub_cmn_mem_1r1w"
DEFAULT_SRAM_BIT_THRESHOLD = 4096
# Legacy files marked for deletion: list only, never totals / baseline compare.
TO_BE_DELETED = frozenset(
    {
        "ub_dll_crc32",
        "ub_dll_crc_check",
        "ub_controller_tx",
        "ub_controller_rx",
    }
)
# Estimate only — not a foundry macro. Revisit when PR #9 §13 sets the node.
SRAM_UM2_PER_BIT = 0.5
SRAM_PERIPH_FACTOR = 1.35
SRAM_FORMULA_LABEL = (
    "SRAM estimate (NOT a real macro): "
    "N_inst × depth × width × 0.5 µm²/bit × 1.35 periphery. "
    "0.5 µm²/bit is an order-of-magnitude SkyWater 130nm 6T bit "
    "(published HD bits ~0.3–0.5 µm²); 1.35 covers decoder / sense-amp / I/O "
    "(textbook 25–50%). Process node pending PR #9 §13 — revisit then. "
    "Liberty stdcell area is a separate column; this one is estimate-only."
)

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

# Legacy tagged-netlist → pre-§2.2 report variant (NUM_LANES=4 was PRODUCT).
_TAG_VARIANT_HINTS = {
    "x4": "PRODUCT",
    "x8": "PRODUCT_NUM_LANES=8",
    "vl2": "PRODUCT",
}


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
    r"(?P<dir>input|output|inout)\s+(?:wire|reg|logic)?\s*"
    r"(?:\[(?P<msb>\d+)\s*:\s*(?P<lsb>\d+)\])?\s*(?P<name>\w+)",
)


def _module_port_blob(verilog: str) -> str:
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
    return blob


def list_ports(verilog: str) -> list[tuple[str, str]]:
    # Only the module header — do not pick up function/task ports.
    return [
        (p.group("dir"), p.group("name"))
        for p in _PORT_RE.finditer(_module_port_blob(verilog))
    ]


def list_port_info(verilog: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in _PORT_RE.finditer(_module_port_blob(verilog)):
        msb, lsb = p.group("msb"), p.group("lsb")
        width = abs(int(msb) - int(lsb)) + 1 if msb is not None else 1
        out.append(
            {
                "dir": p.group("dir"),
                "name": p.group("name"),
                "width": width,
                "msb": int(msb) if msb is not None else 0,
                "lsb": int(lsb) if lsb is not None else 0,
            }
        )
    return out


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
        for base in (
            tree / "rtl" / "pyc_lib",
            tree / "rtl" / "common",
            src.parent,
            tree / "rtl" / "cmn",
            tree / "rtl",
        ):
            cand = (base / inc).resolve()
            if cand.is_file() and cand not in out:
                out.append(cand)
                break
    return out


def is_placeholder_name(name: str) -> bool:
    return name.endswith(PLACEHOLDER_TAG)


def is_to_be_deleted(name: str) -> bool:
    return name in TO_BE_DELETED


def parse_incdirs_env(raw: str | None) -> list[Path]:
    """QS_INCDIRS: colon, comma, or whitespace separated extra -I dirs."""
    if not raw or not raw.strip():
        return []
    parts = re.split(r"[:\s,]+", raw.strip())
    return [Path(p) for p in parts if p]


PYC_LIB_FALLBACK_WARN = (
    "WARN: rtl/pyc_lib/ missing; falling back to rtl/common for Yosys -I "
    "(temporary until #21/#5 land)"
)


def default_pyc_incdir(tree: Path) -> tuple[Path | None, str | None]:
    """Primary include dir is rtl/pyc_lib (TOOLCHAIN.lock-pinned pyCircuit).

    Until #21/#5 copy primitives there, fall back to rtl/common with a WARN.
    """
    pyc_lib = tree / "rtl" / "pyc_lib"
    if pyc_lib.is_dir():
        return pyc_lib.resolve(), None
    common = tree / "rtl" / "common"
    if common.is_dir():
        return common.resolve(), PYC_LIB_FALLBACK_WARN
    return None, (
        "WARN: neither rtl/pyc_lib nor rtl/common exists; `include may fail"
    )


def yosys_incdirs(
    tree: Path, extra: list[Path] | None = None
) -> tuple[list[Path], str | None]:
    """Default -I rtl/pyc_lib (or rtl/common fallback); then --incdir / QS_INCDIRS."""
    dirs: list[Path] = []
    primary, warn = default_pyc_incdir(tree)
    if primary is not None:
        dirs.append(primary)
    for e in extra or []:
        p = e if e.is_absolute() else (tree / e)
        p = p.resolve()
        if p.is_dir() and p not in dirs:
            dirs.append(p)
    return dirs, warn


def is_library_cell(stem: str) -> bool:
    if stem.startswith("pyc_"):
        return True
    if stem == MEM_PRIMITIVE_PREFIX or stem.startswith(MEM_PRIMITIVE_PREFIX + "_"):
        return True
    return False


def is_mem_candidate(name: str, extra_prefixes: set[str] | None = None) -> bool:
    if name == MEM_PRIMITIVE_PREFIX or name.startswith(MEM_PRIMITIVE_PREFIX + "_"):
        return True
    for pref in extra_prefixes or ():
        if name == pref or name.startswith(pref + "_"):
            return True
    return False


def list_rtl_leaves(tree: Path) -> dict[str, dict[str, Path]]:
    """Map filename stem -> {product, hooks?} for rtl/<block>/*.{v,sv}.

    SPEC §2.2: one file per parameter set; module name == filename.
    PRODUCT lives in rtl/<block>/; HOOKS in rtl/<block>/hooks/ with the
    same name. Library cells (any pyc_*, ub_cmn_mem_1r1w*) and rtl/pyc_lib/
    are skipped.
    """
    found: dict[str, dict[str, Path]] = {}
    rtl = tree / "rtl"
    if not rtl.is_dir():
        return found
    for block in sorted(p for p in rtl.iterdir() if p.is_dir()):
        if block.name == "pyc_lib":
            continue
        for path in sorted(block.iterdir()):
            if path.suffix not in {".v", ".sv"} or path.name.endswith(".vh"):
                continue
            if is_library_cell(path.stem):
                continue
            found.setdefault(path.stem, {})["product"] = path
        hooks = block / "hooks"
        if hooks.is_dir():
            for path in sorted(hooks.iterdir()):
                if path.suffix not in {".v", ".sv"}:
                    continue
                if is_library_cell(path.stem):
                    continue
                found.setdefault(path.stem, {})["hooks"] = path
    # rtl/*.v roots (legacy ub_controller_tx/rx) so the exclude list can name them.
    for path in sorted(rtl.iterdir()):
        if path.suffix in {".v", ".sv"} and is_to_be_deleted(path.stem):
            found.setdefault(path.stem, {})["product"] = path
    return found


def default_tops(repo: Path, tree: Path, base: str, head: str | None) -> list[str]:
    """Tops = one module per rtl/<block>/*.v (or hooks/) touched vs base."""
    if head is None:
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
        if not str(p).startswith("rtl/"):
            continue
        if "pyc_lib" in p.parts or is_library_cell(p.stem):
            continue
        if is_to_be_deleted(p.stem):
            tops.append(p.stem)
            continue
        # rtl/<block>/<leaf>.v or rtl/<block>/hooks/<leaf>.v — not rtl/*.v
        if len(p.parts) < 3:
            continue
        tops.append(p.stem)
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
    sta = run(["sta", "-version"], timeout=15)
    sta_ver = (sta.stdout or "").strip().splitlines()[0] if sta.stdout else "unknown"
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


def split_leaf_tag(name: str) -> tuple[str, str | None]:
    """ub_pcs_lane_dist_x4 -> (ub_pcs_lane_dist, 'x4')."""
    if name.endswith(PLACEHOLDER_TAG):
        return name[: -len(PLACEHOLDER_TAG)], "placeholder"
    m = re.search(r"_(x\d+|vl\d+|d\d+w\d+|\d+x\d+)$", name)
    if m:
        return name[: m.start()], m.group(1)
    return name, None


def parse_chparam_arg(s: str) -> tuple[str | None, str, str]:
    """KEY=VAL or TOP:KEY=VAL."""
    if ":" in s and "=" in s and s.index(":") < s.index("="):
        top, rest = s.split(":", 1)
        if "=" not in rest:
            die(f"bad --chparam {s!r} (want KEY=VAL or TOP:KEY=VAL)")
        key, val = rest.split("=", 1)
        return top.strip(), key.strip(), val.strip()
    if "=" not in s:
        die(f"bad --chparam {s!r} (want KEY=VAL or TOP:KEY=VAL)")
    key, val = s.split("=", 1)
    return None, key.strip(), val.strip()


def parse_baseline_map_arg(s: str) -> tuple[str, str, str | None]:
    """NEW=OLD or NEW=OLD:VARIANT (VARIANT may contain '=')."""
    if "=" not in s:
        die(f"bad --baseline-map {s!r} (want NEW=OLD or NEW=OLD:VARIANT)")
    new, rest = s.split("=", 1)
    if ":" in rest:
        old, var = rest.split(":", 1)
        return new.strip(), old.strip(), var.strip() or None
    return new.strip(), rest.strip(), None


def _parse_num(s: str) -> float | int | None:
    s = (s or "").strip().replace(",", "")
    if s in {"", "—", "-", "n/a", "NA", "new"}:
        return None
    try:
        if re.fullmatch(r"-?\d+", s):
            return int(s)
        return float(s)
    except ValueError:
        return None


def parse_baseline_markdown(text: str) -> list[dict[str, Any]]:
    """Parse a prior quick-synth markdown table into result-like dicts."""
    rows: list[dict[str, Any]] = []
    in_table = False
    header: list[str] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            if in_table and rows:
                break
            in_table = False
            header = []
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cols:
            continue
        if cols[0].lower() == "module" and any(
            "variant" in c.lower() for c in cols
        ):
            in_table = True
            header = [c.lower() for c in cols]
            continue
        if not in_table:
            continue
        if cols[0].startswith("---") or set(cols[0]) <= {"-", ":"}:
            continue
        if len(cols) < 6:
            continue

        def col(*names: str) -> str:
            for n in names:
                if n in header:
                    return cols[header.index(n)] if header.index(n) < len(cols) else ""
            return ""

        rows.append(
            {
                "top": cols[0],
                "variant": cols[1] if len(cols) > 1 else "PRODUCT",
                "cells_mapped": _parse_num(
                    col("cells (mapped)", "cells") or (cols[2] if len(cols) > 2 else "")
                ),
                "area_um2": _parse_num(
                    col("area um^2", "area") or (cols[3] if len(cols) > 3 else "")
                ),
                "flops": _parse_num(col("flops") or (cols[4] if len(cols) > 4 else "")),
                "logic_depth": _parse_num(
                    col("max comb logic depth", "logic depth")
                    or (cols[5] if len(cols) > 5 else "")
                ),
                "arrival_ns": _parse_num(
                    col("arrival ns") or (cols[6] if len(cols) > 6 else "")
                ),
                "slack_ns": _parse_num(
                    col("slack @ period", "slack")
                    or (cols[7] if len(cols) > 7 else "")
                ),
                "ok": True,
            }
        )
    return rows


def load_baseline_rows(
    json_path: Path | None, report_path: Path | None
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if report_path is not None:
        rows.extend(
            parse_baseline_markdown(
                report_path.read_text(encoding="utf-8", errors="replace")
            )
        )
    if json_path is not None:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        payload = data.get("results", data if isinstance(data, list) else [])
        by_key = {(r.get("top"), r.get("variant")): r for r in rows}
        for r in payload:
            by_key[(r.get("top"), r.get("variant"))] = r
        rows = list(by_key.values())
    return rows


def find_baseline_row(
    rows: list[dict[str, Any]], top: str, variant: str | None
) -> dict[str, Any] | None:
    if variant is not None:
        for r in rows:
            if r.get("top") == top and r.get("variant") == variant:
                return r
    for r in rows:
        if r.get("top") == top and r.get("variant") == "PRODUCT":
            return r
    for r in rows:
        if r.get("top") == top:
            return r
    return None


def resolve_baseline(
    top: str,
    variant: str,
    rows: list[dict[str, Any]],
    maps: dict[str, tuple[str, str | None]],
) -> tuple[dict[str, Any] | None, str]:
    """Return (baseline row, how it was chosen)."""
    if top in maps:
        old, old_var = maps[top]
        want = old_var or variant
        hit = find_baseline_row(rows, old, want)
        if hit is None and old_var is None and variant == "HOOKS":
            hit = find_baseline_row(rows, old, "PRODUCT")
        label = f"{old} {hit.get('variant') if hit else want}"
        return hit, f"map {top} → {label}"
    if variant == "HOOKS":
        hit = find_baseline_row(rows, top, "HOOKS") or find_baseline_row(
            rows, top, "PRODUCT"
        )
        if hit:
            return hit, f"same name {top} {hit.get('variant')}"
    hit = find_baseline_row(rows, top, variant)
    if hit:
        return hit, f"same name {top} {variant}"
    stem, tag = split_leaf_tag(top)
    if tag and tag != "placeholder":
        want = _TAG_VARIANT_HINTS.get(tag)
        m = re.fullmatch(r"x(\d+)", tag or "")
        if want:
            hit = find_baseline_row(rows, stem, want)
            if hit:
                return hit, f"tag _{tag} → {stem} {want}"
        if m:
            n = m.group(1)
            want_n = "PRODUCT" if n == "4" else f"PRODUCT_NUM_LANES={n}"
            hit = find_baseline_row(rows, stem, want_n)
            if hit:
                return hit, f"tag _{tag} → {stem} {want_n} (legacy NUM_LANES={n})"
        hit = find_baseline_row(rows, stem, "PRODUCT")
        if hit:
            return hit, f"tag _{tag} → {stem} PRODUCT"
    return None, "new"


def qor_compare(new: dict[str, Any], old: dict[str, Any]) -> dict[str, Any]:
    flags: list[str] = []
    parts: list[str] = []
    for field in QOR_COMPARE_FIELDS:
        nv, ov = new.get(field), old.get(field)
        short = QOR_FIELD_SHORT[field]
        if nv is None or ov is None:
            continue
        nv_f, ov_f = float(nv), float(ov)
        if ov_f == 0 and nv_f == 0:
            parts.append(f"{short} 0 vs 0")
            continue
        if ov_f == 0:
            flags.append(short)
            parts.append(f"{short} {fmt_num(nv)} vs 0")
            continue
        rel = abs(nv_f - ov_f) / abs(ov_f)
        signed = (nv_f - ov_f) / abs(ov_f)
        parts.append(
            f"{short} {fmt_num(nv)} vs {fmt_num(ov)} ({signed:+.1%})"
        )
        if rel > QOR_DELTA_THRESHOLD:
            flags.append(short)
    return {
        "delta_vs_baseline": "; ".join(parts) if parts else "new",
        "qor_over_10pct": flags,
    }


def load_blackbox_yml(path: Path) -> list[dict[str, Any]]:
    """Parse scripts/gate/blackbox.yml if present (no PyYAML required)."""
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        data = json.loads(text)
        if isinstance(data, list):
            return [_bb_entry(x) for x in data if _bb_entry(x)]
        mods = data.get("modules", [])
        return [_bb_entry(x) for x in mods if _bb_entry(x)]
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_modules = False
    for raw in text.splitlines():
        if raw.strip().startswith("#") or not raw.strip():
            continue
        if re.match(r"^modules\s*:", raw):
            in_modules = True
            continue
        if not in_modules:
            # bare list at top level
            in_modules = True
        m = re.match(r"^(\s*)-\s+(?:name\s*:\s*)?(.+?)\s*$", raw)
        if m:
            if current:
                entries.append(current)
            val = m.group(2).strip().strip("'\"")
            if re.match(r"^\w", val) and ":" not in val:
                current = {"name": val}
            elif val.startswith("name"):
                current = {"name": val.split(":", 1)[-1].strip().strip("'\"")}
            else:
                current = {}
                km = re.match(r"(\w+)\s*:\s*(.+)$", val)
                if km:
                    current[km.group(1)] = _yaml_scalar(km.group(2))
            continue
        km = re.match(r"^\s+(\w+)\s*:\s*(.+)$", raw)
        if km and current is not None:
            current[km.group(1)] = _yaml_scalar(km.group(2))
    if current:
        entries.append(current)
    return [e for e in entries if e.get("name")]


def _yaml_scalar(s: str) -> Any:
    s = s.strip().strip("'\"")
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return s


def _bb_entry(x: Any) -> dict[str, Any] | None:
    if isinstance(x, str) and x.strip():
        return {"name": x.strip()}
    if isinstance(x, dict) and x.get("name"):
        return dict(x)
    return None


def find_module_file(tree: Path, name: str) -> Path | None:
    rtl = tree / "rtl"
    if not rtl.is_dir():
        return None
    for ext in (".v", ".sv"):
        for path in rtl.rglob(name + ext):
            if "hooks" in path.parts:
                continue
            return path
    return None


def list_mem_files(tree: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    rtl = tree / "rtl"
    if not rtl.is_dir():
        return found
    for path in rtl.rglob("*"):
        if path.suffix not in {".v", ".sv"}:
            continue
        if is_mem_candidate(path.stem):
            if "hooks" in path.parts and path.stem in found:
                continue
            found[path.stem] = path
    return found


def parse_mem_dims(
    name: str,
    verilog: str | None,
    yml_hint: dict[str, Any] | None = None,
) -> tuple[int | None, int | None, str]:
    if yml_hint and yml_hint.get("depth") and yml_hint.get("width"):
        return int(yml_hint["depth"]), int(yml_hint["width"]), "blackbox.yml"
    m = re.search(r"_d(\d+)w(\d+)", name)
    if m:
        return int(m.group(1)), int(m.group(2)), "module tag _d<D>w<W>"
    m = re.search(r"_(\d+)x(\d+)", name)
    if m:
        return int(m.group(1)), int(m.group(2)), "module tag _<D>x<W>"
    if verilog:
        ma = re.search(
            r"(?:reg|logic)\s+\[(\d+)\s*:\s*(\d+)\]\s+\w+\s*"
            r"\[\s*(\d+)\s*:\s*(\d+)\s*\]",
            verilog,
        )
        if ma:
            width = abs(int(ma.group(1)) - int(ma.group(2))) + 1
            depth = abs(int(ma.group(3)) - int(ma.group(4))) + 1
            return depth, width, "storage array declaration"
        ports = list_port_info(verilog)
        rdata = pick_rdata_port(ports)
        addr = pick_raddr_port(ports)
        if rdata and addr:
            depth = 1 << addr["width"]
            return depth, rdata["width"], "port widths (depth=2^raddr)"
        if rdata:
            return None, rdata["width"], "rdata port width only"
    return None, None, "unknown"


def pick_rdata_port(ports: list[dict[str, Any]]) -> dict[str, Any] | None:
    outs = [p for p in ports if p["dir"] in ("output", "inout")]
    prefer = (
        "rdata",
        "rd_data",
        "rd_dout",
        "dout",
        "q",
        "rd_q",
        "data_out",
    )
    by_name = {p["name"]: p for p in outs}
    for n in prefer:
        if n in by_name:
            return by_name[n]
    if not outs:
        return None
    return max(outs, key=lambda p: p["width"])


def pick_raddr_port(ports: list[dict[str, Any]]) -> dict[str, Any] | None:
    ins = [p for p in ports if p["dir"] in ("input", "inout")]
    prefer = ("raddr", "rd_addr", "ra", "addr_r", "rd_adr")
    by_name = {p["name"]: p for p in ins}
    for n in prefer:
        if n in by_name:
            return by_name[n]
    return None


def count_instances(verilog: str, mod: str) -> int:
    return len(
        re.findall(
            rf"\b{re.escape(mod)}(?:\s+#\s*\([^;]*\))?\s+\w+\s*\(",
            verilog,
        )
    )


def find_instantiated(verilog: str, known: set[str]) -> list[str]:
    found: list[str] = []
    for name in sorted(known, key=len, reverse=True):
        if count_instances(verilog, name):
            found.append(name)
    return found


def sram_estimate_um2(n_inst: int, depth: int, width: int) -> float:
    return n_inst * depth * width * SRAM_UM2_PER_BIT * SRAM_PERIPH_FACTOR


def write_mem_sta_stub(
    module: str,
    verilog: str,
    dest: Path,
) -> dict[str, Any]:
    """Emit a structural 1-cycle registered-read stub for OpenSTA.

    Storage is not modeled. Each rdata bit is a sky130_fd_sc_hd__dfxtp_1
    with D tied 0 so the output is a register launch into downstream logic.
    """
    ports = list_port_info(verilog)
    clk = find_clock_port(verilog)
    rdata = pick_rdata_port(ports)
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"// STA stub: 1-cycle registered read for {module}", f"module {module} ("]
    names = [p["name"] for p in ports] or ["clk", "rdata"]
    lines.append("  " + ",\n  ".join(names))
    lines.append(");")
    if not ports:
        lines.append("  input clk;")
        lines.append("  output rdata;")
    for p in ports:
        if p["width"] > 1:
            rng = f" [{p['msb']}:{p['lsb']}]"
        else:
            rng = ""
        lines.append(f"  {p['dir']}{rng} {p['name']};")
    info: dict[str, Any] = {
        "module": module,
        "clk": clk,
        "rdata": rdata["name"] if rdata else None,
        "rdata_width": rdata["width"] if rdata else None,
        "registered": bool(clk and rdata),
    }
    if clk and rdata:
        w = rdata["width"]
        rn = rdata["name"]
        if w == 1:
            lines.append(
                f"  sky130_fd_sc_hd__dfxtp_1 {rn}_q ("
                f" .CLK({clk}), .D(1'b0), .Q({rn}) );"
            )
        else:
            lsb = rdata["lsb"]
            step = 1 if rdata["msb"] >= rdata["lsb"] else -1
            for i in range(w):
                idx = lsb + i * step
                lines.append(
                    f"  sky130_fd_sc_hd__dfxtp_1 {rn}_q_{i} ("
                    f" .CLK({clk}), .D(1'b0), .Q({rn}[{idx}]) );"
                )
    elif rdata and rdata["width"] > 1:
        lines.append(f"  assign {rdata['name']} = {rdata['width']}'b0;")
    elif rdata:
        lines.append(f"  assign {rdata['name']} = 1'b0;")
    lines.append("endmodule")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return info


def build_mem_catalog(
    tree: Path,
    sram_bit_threshold: int,
    bb_entries: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    extra = {e["name"] for e in bb_entries}
    hints = {e["name"]: e for e in bb_entries}
    catalog: dict[str, dict[str, Any]] = {}
    files = list_mem_files(tree)
    names = set(files) | extra
    # Also pick up §2.2 tagged variants of yml prefixes.
    for path_name, path in list(files.items()):
        names.add(path_name)
        catalog.setdefault(path_name, {})
    for name in extra:
        if name not in files:
            found = find_module_file(tree, name)
            if found:
                files[name] = found
            for path_name, path in list_mem_files(tree).items():
                if is_mem_candidate(path_name, extra):
                    files[path_name] = path
                    names.add(path_name)
    for name in sorted(set(files) | extra):
        path = files.get(name) or find_module_file(tree, name)
        text = (
            path.read_text(encoding="utf-8", errors="replace") if path else None
        )
        hint = hints.get(name)
        if hint is None:
            for pref, h in hints.items():
                if name == pref or name.startswith(pref + "_"):
                    hint = h
                    break
        depth, width, src = parse_mem_dims(name, text, hint)
        bits = (
            depth * width if depth is not None and width is not None else None
        )
        catalog[name] = {
            "name": name,
            "path": path,
            "depth": depth,
            "width": width,
            "bits": bits,
            "dim_source": src,
            "blackbox": bool(bits is not None and bits > sram_bit_threshold),
        }
    return catalog


def classify_mem_in_src(
    src_text: str,
    catalog: dict[str, dict[str, Any]],
    sram_bit_threshold: int,
) -> dict[str, Any]:
    known = set(catalog)
    inst_mods = find_instantiated(src_text, known)
    blackbox: list[dict[str, Any]] = []
    flopped: list[dict[str, Any]] = []
    est = 0.0
    for mod in inst_mods:
        rec = catalog[mod]
        n = count_instances(src_text, mod)
        bits = rec.get("bits")
        entry = {
            **rec,
            "n_inst": n,
            "path": str(rec["path"]) if rec.get("path") else None,
        }
        if bits is not None and bits > sram_bit_threshold:
            entry["blackbox"] = True
            entry["est_um2"] = sram_estimate_um2(n, rec["depth"], rec["width"])
            est += entry["est_um2"]
            blackbox.append(entry)
        else:
            entry["blackbox"] = False
            entry["est_um2"] = 0.0
            flopped.append(entry)
    return {
        "blackbox": blackbox,
        "flopped": flopped,
        "sram_est_um2": est,
        "sram_bits": sum(
            (b["bits"] or 0) * b["n_inst"] for b in blackbox
        ),
    }


def emit_buffered_mapped(
    *,
    json_in: Path,
    json_out: Path,
    verilog_out: Path,
    stat_out: Path,
    liberty: Path,
    top: str,
) -> subprocess.CompletedProcess[str]:
    """read_json the buffered netlist and write mapped.v + liberty stat."""
    cmd = (
        f"read_liberty -lib {liberty}; "
        f"read_json {json_in}; "
        f"hierarchy -top {top}; "
        f"tee -o {stat_out} stat -liberty {liberty}; "
        f"write_verilog -noattr -noexpr {verilog_out}"
    )
    return run(["yosys", "-p", cmd], timeout=300)


def synthesize_one(
    *,
    top: str,
    src: Path,
    tree: Path,
    outdir: Path,
    liberty: Path,
    chparam_override: dict[str, str] | None,
    period_ns: float,
    variant: str,
    mem_catalog: dict[str, dict[str, Any]],
    sram_bit_threshold: int,
    extra_incdirs: list[Path] | None = None,
    buffer: bool = True,
    max_fanout_limit: int = DEFAULT_MAX_FANOUT,
) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    files = [src]
    # Do not also list `include targets in QS_FILES — Yosys -I resolves
    # them; a second read_verilog redefines pyc_reg.

    text = src.read_text(encoding="utf-8", errors="replace")
    clk = find_clock_port(text)
    ports = list_ports(text)
    in_ports = [n for d, n in ports if d in ("input", "inout") and n != clk]
    out_ports = [n for d, n in ports if d in ("output", "inout")]

    mem_use = classify_mem_in_src(text, mem_catalog, sram_bit_threshold)
    lib_files: list[Path] = []
    stubs: list[Path] = []
    notes: list[str] = []
    for rec in mem_use["flopped"]:
        p = rec.get("path")
        if p:
            fp = Path(p)
            if fp.is_file() and fp not in files:
                files.append(fp)
                notes.append(
                    f"{rec['name']} {rec['depth']}x{rec['width']}="
                    f"{rec['bits']} bits ≤ {sram_bit_threshold}; synth as flops"
                )
    for rec in mem_use["blackbox"]:
        p = rec.get("path")
        if p:
            fp = Path(p)
            if fp.is_file():
                lib_files.append(fp)
                stub = outdir / f"sta_stub_{rec['name']}.v"
                src_v = fp.read_text(encoding="utf-8", errors="replace")
                info = write_mem_sta_stub(rec["name"], src_v, stub)
                stubs.append(stub)
                launch = (
                    "STA rdata is a 1-cycle registered launch"
                    if info.get("registered")
                    else "STA stub has no clock; rdata tied 0"
                )
                notes.append(
                    f"blackbox {rec['name']} {rec['n_inst']}× "
                    f"{rec['depth']}x{rec['width']}={rec['bits']} bits "
                    f"(>{sram_bit_threshold}); SRAM est "
                    f"{rec['est_um2']:.1f} um^2; {launch}"
                )
        else:
            notes.append(f"blackbox {rec['name']}: netlist not found in tree")

    merged: dict[str, str] = {}
    if chparam_override:
        for k, v in chparam_override.items():
            if re.search(rf"\bparameter\b[^;]*\b{re.escape(k)}\b", text):
                merged[k] = v
                notes.append(f"optional chparam override {k}={v}")
            else:
                notes.append(
                    f"chparam override {k} skipped "
                    "(no Verilog parameter; SPEC §2.2 fixed netlist)"
                )

    ch_cmd = ""
    if merged:
        parts = [f"-set {k} {v}" for k, v in merged.items()]
        ch_cmd = "chparam " + " ".join(parts) + f" {top}"

    env = os.environ.copy()
    incdirs, inc_warn = yosys_incdirs(tree, extra_incdirs)
    if inc_warn:
        notes.append(inc_warn)
    env["QS_TOP"] = top
    env["QS_FILES"] = " ".join(str(p) for p in files)
    env["QS_LIB_FILES"] = " ".join(str(p) for p in lib_files)
    env["QS_INCDIRS"] = " ".join(str(p) for p in incdirs)
    env["QS_LIBERTY"] = str(liberty)
    env["QS_OUTDIR"] = str(outdir)
    env["QS_CHPARAM"] = ch_cmd
    env["QS_READ_SV"] = (
        "1"
        if src.suffix == ".sv" or any(p.suffix == ".sv" for p in files)
        else "0"
    )

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
        "placeholder": is_placeholder_name(top),
        "sram_est_um2": mem_use["sram_est_um2"],
        "sram_bits": mem_use["sram_bits"],
        "sram_blackbox": [
            {k: v for k, v in b.items() if k != "path"} for b in mem_use["blackbox"]
        ],
        "sram_flopped": [
            {k: v for k, v in b.items() if k != "path"} for b in mem_use["flopped"]
        ],
    }
    if y.returncode != 0:
        result["error"] = "yosys failed"
        result["log_excerpt"] = _excerpt(y.stdout or "")
        result["anomalies"] = ["yosys_failed"]
        return result

    fanout_rep: dict[str, Any] = {
        "enabled": bool(buffer),
        "method": "none",
        "max_fanout_limit": max_fanout_limit,
        "max_fanout_before": None,
        "max_fanout_after": None,
        "n_bufs": 0,
        "n_nets_buffered": 0,
    }
    prebuf_json = outdir / "mapped_prebuf.json"
    if prebuf_json.is_file():
        pre_data = json.loads(prebuf_json.read_text(encoding="utf-8"))
        if buffer:
            buf_data, fanout_rep = buffer_design(pre_data, max_fanout_limit)
            fanout_rep["enabled"] = True
            buf_json = outdir / "mapped_buf.json"
            buf_json.write_text(
                json.dumps(buf_data, indent=2) + "\n", encoding="utf-8"
            )
            if int(fanout_rep.get("n_bufs") or 0) > 0:
                y2 = emit_buffered_mapped(
                    json_in=buf_json,
                    json_out=buf_json,
                    verilog_out=outdir / "mapped.v",
                    stat_out=outdir / "mapped_stat.txt",
                    liberty=liberty,
                    top=top,
                )
                (outdir / "yosys_buffer.log").write_text(
                    y2.stdout or "", encoding="utf-8"
                )
                if y2.returncode != 0:
                    result["error"] = "fanout buffer yosys emit failed"
                    result["log_excerpt"] = _excerpt(y2.stdout or "")
                    result["anomalies"] = ["yosys_failed"]
                    result["ok"] = False
                    result["fanout"] = fanout_rep
                    return result
                notes.append(
                    f"fanout buffer {fanout_rep['method']}: "
                    f"max {fanout_rep['max_fanout_before']}→"
                    f"{fanout_rep['max_fanout_after']} "
                    f"(+{fanout_rep['n_bufs']} buf, "
                    f"{fanout_rep['n_nets_buffered']} nets, "
                    f"limit {max_fanout_limit})"
                )
            else:
                notes.append(
                    f"fanout buffer {fanout_rep['method']}: "
                    f"no net above {max_fanout_limit} "
                    f"(max {fanout_rep['max_fanout_before']})"
                )
        else:
            fanout_rep = analyze_design(pre_data)
            fanout_rep["enabled"] = False
            fanout_rep["max_fanout_limit"] = max_fanout_limit
            notes.append(
                f"fanout buffer off (--no-buffer); "
                f"max fanout {fanout_rep['max_fanout_before']}"
            )
        (outdir / "fanout_report.json").write_text(
            json.dumps(fanout_rep, indent=2) + "\n", encoding="utf-8"
        )
    else:
        notes.append("mapped_prebuf.json missing; fanout not measured")

    result["fanout"] = fanout_rep
    result["max_fanout"] = fanout_rep.get("max_fanout_after")
    result["max_fanout_before"] = fanout_rep.get("max_fanout_before")
    result["buffer_method"] = fanout_rep.get("method")
    result["n_bufs"] = fanout_rep.get("n_bufs")

    designer = parse_stat((outdir / "designer_stat.txt").read_text(errors="replace"))
    generic = parse_stat(
        (outdir / "generic_synth_stat.txt").read_text(errors="replace")
    )
    mapped = parse_stat((outdir / "mapped_stat.txt").read_text(errors="replace"))
    if mapped["cells"] == 0 and mapped["area_um2"] is None:
        mapped["area_um2"] = 0.0
    n_bb = sum(b["n_inst"] for b in mem_use["blackbox"])
    cells = mapped["cells"]
    if cells is not None and n_bb:
        cells = max(0, cells - n_bb)
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
            "cells_mapped": cells,
            "area_um2": mapped["area_um2"],
            "flops": mapped["flops"],
            "ltp": ltp,
            "comb_loops": loops,
            "latches_generic": latch_sel,
            "mem_generic": mem_sel,
        }
    )

    mapped_v = outdir / "mapped.v"
    env["QS_NETLIST"] = str(mapped_v)
    env["QS_PERIOD_NS"] = f"{period_ns:.9f}"
    env["QS_CLK_PORT"] = clk or ""
    env["QS_CLK_NAME"] = "core_clk"
    env["QS_INPUTS"] = " ".join(in_ports)
    env["QS_OUTPUTS"] = " ".join(out_ports)
    env["QS_STUB_FILES"] = " ".join(str(p) for p in stubs)
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
    if r.get("mem_generic") and not r.get("sram_blackbox") and not r.get("sram_flopped"):
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
    wiring_only = (
        cells == 0 and (proc_cells in (0, None)) and not sequential_src
    )
    if wiring_only:
        r.setdefault("notes", []).append(
            "combinational wiring only (0 std cells after map; bit permute / assign)"
        )
    elif cells == 0 and not r.get("sram_blackbox"):
        a.append("near_zero_cells_after_map (module optimized away)")
    elif sequential_src and flops == 0 and cells is not None and cells <= 2:
        a.append("near_zero_cells_after_map (possible unused/undriven sweep)")
    if area is not None and area > 20000 and not r.get("sram_flopped"):
        a.append(f"unexpectedly_large_area {area:.1f} um^2")
    if cells is not None and cells > 8000:
        a.append(f"unexpectedly_large_cell_count {cells}")
    if re.search(r"removing unused", yosys_log, re.IGNORECASE):
        if cells == 0 and not r.get("sram_blackbox"):
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
        "| module | variant | cells (mapped) | area um^2 | SRAM est um^2 | flops | "
        "max fanout | max comb logic depth | arrival ns | slack @ period | "
        "vs baseline | QoR >10% | notes |"
    )
    sep = (
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |"
    )
    lines = [hdr, sep]
    for r in rows:
        notes = "; ".join(r.get("notes") or [])
        an = r.get("anomalies") or []
        if an:
            notes = (("ANOMALY: " + "; ".join(an) + ". ") + notes).strip()
        if r.get("error"):
            notes = f"FAIL: {r['error']}. " + notes
        flags = r.get("qor_over_10pct") or []
        flag_s = ",".join(flags) if flags else "—"
        delta = r.get("delta_vs_baseline") or r.get("delta_vs_main") or "new"
        lines.append(
            "| {mod} | {var} | {cells} | {area} | {sram} | {flops} | {fo} | "
            "{depth} | {arr} | {sl} | {delta} | {flag} | {notes} |".format(
                mod=r.get("top", ""),
                var=r.get("variant", ""),
                cells=fmt_num(r.get("cells_mapped"), 0),
                area=fmt_num(r.get("area_um2"), 1),
                sram=fmt_num(r.get("sram_est_um2"), 1),
                flops=fmt_num(r.get("flops"), 0),
                fo=fmt_num(r.get("max_fanout"), 0),
                depth=fmt_num(r.get("logic_depth"), 0),
                arr=fmt_num(r.get("arrival_ns"), 3),
                sl=fmt_num(r.get("slack_ns"), 3),
                delta=str(delta).replace("|", "/"),
                flag=flag_s,
                notes=notes.replace("|", "/") or "—",
            )
        )
    return "\n".join(lines)


def product_area_totals(rows: list[dict[str, Any]]) -> dict[str, float]:
    prod = [
        r
        for r in rows
        if r.get("variant") == "PRODUCT"
        and not is_placeholder_name(r.get("top") or "")
        and not r.get("to_be_deleted")
        and not is_to_be_deleted(r.get("top") or "")
        and r.get("ok")
    ]
    return {
        "area_um2": sum((r.get("area_um2") or 0) for r in prod),
        "sram_est_um2": sum((r.get("sram_est_um2") or 0) for r in prod),
        "n": float(len(prod)),
    }


def write_full_markdown(
    rows: list[dict[str, Any]], inc_warn: str | None = None
) -> str:
    deleted = [
        r
        for r in rows
        if r.get("to_be_deleted") or is_to_be_deleted(r.get("top") or "")
    ]
    ph_rows = [
        r
        for r in rows
        if is_placeholder_name(r.get("top") or "") and r not in deleted
    ]
    main_rows = [r for r in rows if r not in deleted and r not in ph_rows]
    totals = product_area_totals(rows)
    parts: list[str] = []
    if inc_warn:
        parts.extend([inc_warn, ""])
    parts.extend(
        [
            "## PRODUCT / HOOKS",
            "",
            write_markdown_table(main_rows) if main_rows else "_no PRODUCT/HOOKS leaves_",
            "",
            (
                f"**PRODUCT area total** (non-placeholder PRODUCT rows only; "
                f"HOOKS, `_placeholder`, and 待删除 / to be deleted excluded): "
                f"{totals['area_um2']:.1f} um^2 stdcell, "
                f"{totals['sram_est_um2']:.1f} um^2 SRAM estimate "
                f"({int(totals['n'])} leaves)."
            ),
        ]
    )
    if deleted:
        parts.extend(
            [
                "",
                "## 待删除 / to be deleted",
                "",
                "| module | path | notes |",
                "| --- | --- | --- |",
            ]
        )
        for r in deleted:
            parts.append(
                "| {mod} | {src} | {notes} |".format(
                    mod=r.get("top", ""),
                    src=r.get("src") or "—",
                    notes="; ".join(r.get("notes") or []) or "legacy; excluded",
                )
            )
    if ph_rows:
        parts.extend(
            [
                "",
                "## `_placeholder` (lint / TB only; excluded from PRODUCT area totals)",
                "",
                write_markdown_table(ph_rows),
            ]
        )
    flagged = [
        r
        for r in rows
        if r.get("qor_over_10pct")
    ]
    if flagged:
        parts.extend(["", "## QoR flags (>10% vs baseline)", ""])
        for r in flagged:
            parts.append(
                f"- `{r.get('top')}` {r.get('variant')}: "
                + ", ".join(r["qor_over_10pct"])
                + f" — {r.get('delta_vs_baseline', '')}"
            )
    return "\n".join(parts)


def self_check() -> int:
    """Parser / mapping / estimate checks. No design-PR synth."""
    failures: list[str] = []

    def expect(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    expect(is_placeholder_name("ub_pcs_scrambler_placeholder"), "placeholder suffix")
    expect(not is_placeholder_name("ub_pcs_scrambler"), "non-placeholder")
    expect(is_library_cell("ub_cmn_mem_1r1w_d128w64"), "mem is library cell")
    expect(is_library_cell("pyc_reg"), "pyc_reg is library")
    expect(is_library_cell("pyc_foo"), "any pyc_* is library")
    expect(not is_library_cell("ub_pcs_lane_dist_x4"), "leaf is not library")
    expect(not is_library_cell("ub_pyc_rst_adapt"), "ub_pyc_* is a leaf")
    expect(is_to_be_deleted("ub_dll_crc32"), "crc32 to-be-deleted")
    expect(is_to_be_deleted("ub_controller_tx"), "controller_tx to-be-deleted")
    expect(not is_to_be_deleted("ub_dll_bcrc"), "bcrc is live")
    expect(
        count_instances(
            "  ub_cmn_mem_1r1w_d128w64 u_mem (\n    .clk(clk)\n  );\n",
            "ub_cmn_mem_1r1w_d128w64",
        )
        == 1,
        "count_instances single-space inst",
    )

    d, w, src = parse_mem_dims("ub_cmn_mem_1r1w_d128w64", None)
    expect((d, w) == (128, 64) and "tag" in src, f"tag dims {d}x{w} {src}")
    d, w, src = parse_mem_dims(
        "ub_cmn_mem_1r1w",
        "module m; reg [31:0] mem [0:255]; endmodule",
    )
    expect((d, w) == (256, 32), f"array dims {d}x{w}")
    est = sram_estimate_um2(1, 128, 64)
    expect(abs(est - 8192 * 0.5 * 1.35) < 1e-6, f"sram est {est}")
    expect(8192 > DEFAULT_SRAM_BIT_THRESHOLD, "8192 is large")
    expect(1024 <= DEFAULT_SRAM_BIT_THRESHOLD, "1024 is small")

    md = """
| Item | Value |
| --- | --- |
| PR | #5 |

| module | variant | cells | area um^2 | flops | logic depth | arrival ns | slack @ period | delta vs main | notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| ub_pcs_lane_dist | PRODUCT | 0 | 0.0 | 0 | 0 | 0.001 | 12.412 | new | wiring |
| ub_pcs_lane_dist | PRODUCT_NUM_LANES=8 | 0 | 0.0 | 0 | 0 | 0.001 | 12.412 | new | wiring |
| ub_dll_bcrc | PRODUCT | 1659 | 17559.3 | 61 | 75 | 33.918 | -21.630 | new | slack |
"""
    brows = parse_baseline_markdown(md)
    expect(len(brows) == 3, f"parsed {len(brows)} baseline rows")
    hit, how = resolve_baseline(
        "ub_pcs_lane_dist_x4", "PRODUCT", brows, {}
    )
    expect(
        hit is not None and hit["top"] == "ub_pcs_lane_dist" and hit["variant"] == "PRODUCT",
        f"x4 map {hit} {how}",
    )
    hit, how = resolve_baseline(
        "ub_pcs_lane_dist_x8", "PRODUCT", brows, {}
    )
    expect(
        hit is not None and hit.get("variant") == "PRODUCT_NUM_LANES=8",
        f"x8 map {hit} {how}",
    )
    hit, how = resolve_baseline("ub_dll_bcrc", "PRODUCT", brows, {})
    expect(hit is not None and hit["cells_mapped"] == 1659, f"bcrc same name {hit}")
    hit, how = resolve_baseline(
        "ub_pcs_lane_dist_x4",
        "PRODUCT",
        brows,
        {"ub_pcs_lane_dist_x4": ("ub_pcs_lane_dist", "PRODUCT")},
    )
    expect(hit is not None and "map" in how, f"explicit map {how}")

    cmpd = qor_compare(
        {"cells_mapped": 100, "area_um2": 100.0, "logic_depth": 10, "slack_ns": 1.0},
        {"cells_mapped": 100, "area_um2": 100.0, "logic_depth": 10, "slack_ns": 1.0},
    )
    expect(cmpd["qor_over_10pct"] == [], f"no flag {cmpd}")
    cmpd = qor_compare(
        {"cells_mapped": 120, "area_um2": 100.0, "logic_depth": 10, "slack_ns": 1.0},
        {"cells_mapped": 100, "area_um2": 100.0, "logic_depth": 10, "slack_ns": 1.0},
    )
    expect("cells" in cmpd["qor_over_10pct"], f"cells 20% {cmpd}")
    cmpd = qor_compare(
        {"cells_mapped": 0, "area_um2": 0.0, "logic_depth": 0, "slack_ns": 12.4},
        {"cells_mapped": 0, "area_um2": 0.0, "logic_depth": 0, "slack_ns": 12.4},
    )
    expect(cmpd["qor_over_10pct"] == [], f"zero vs zero {cmpd}")

    yml = load_blackbox_yml  # exercise parser on a temp file
    with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as tf:
        tf.write("modules:\n  - ub_cmn_mem_1r1w\n  - name: other_mem\n    depth: 512\n    width: 16\n")
        tf.flush()
        parsed = load_blackbox_yml(Path(tf.name))
    expect(
        len(parsed) == 2 and parsed[1].get("depth") == 512,
        f"yml parse {parsed}",
    )

    stub_v = (
        "module ub_cmn_mem_1r1w_d4w8 (\n"
        "  input clk,\n  input we,\n  input [1:0] waddr,\n"
        "  input [7:0] wdata,\n  input [1:0] raddr,\n  output [7:0] rdata\n);\n"
        "endmodule\n"
    )
    with tempfile.TemporaryDirectory() as td:
        info = write_mem_sta_stub(
            "ub_cmn_mem_1r1w_d4w8", stub_v, Path(td) / "stub.v"
        )
        body = (Path(td) / "stub.v").read_text()
    expect(info.get("registered") is True, f"stub registered {info}")
    expect(body.count("sky130_fd_sc_hd__dfxtp_1") == 8, "8 rdata flops")

    with tempfile.TemporaryDirectory() as td:
        tree = Path(td)
        (tree / "rtl" / "pyc_lib").mkdir(parents=True)
        (tree / "rtl" / "dll").mkdir(parents=True)
        (tree / "rtl" / "pyc_lib" / "qs_inc_cell.v").write_text(
            "module qs_inc_cell (input a, output y); assign y = a; endmodule\n",
            encoding="utf-8",
        )
        leaf = tree / "rtl" / "dll" / "ub_qs_inc_leaf.v"
        leaf.write_text(
            '`include "qs_inc_cell.v"\n'
            "module ub_qs_inc_leaf (input a, output y);\n"
            "  qs_inc_cell u (.a(a), .y(y));\n"
            "endmodule\n",
            encoding="utf-8",
        )
        dirs, warn = yosys_incdirs(tree)
        expect(warn is None, f"no fallback warn when pyc_lib exists: {warn}")
        expect(any(p.name == "pyc_lib" for p in dirs), f"incdirs {dirs}")
        if not shutil.which("yosys"):
            failures.append("yosys missing; include-read self-test not run")
        else:
            inc = " ".join(f"-I {d}" for d in dirs)
            cp = run(
                [
                    "yosys",
                    "-p",
                    f"read_verilog {inc} {leaf}; hierarchy -check -top ub_qs_inc_leaf",
                ]
            )
            expect(
                cp.returncode == 0,
                f"yosys include read failed:\n{(cp.stdout or '')[-400:]}",
            )

    expect(choose_buf(1) == "sky130_fd_sc_hd__buf_4", "buf_4 for small group")
    expect(choose_buf(4) == "sky130_fd_sc_hd__buf_4", "buf_4 at 4")
    expect(choose_buf(5) == "sky130_fd_sc_hd__buf_8", "buf_8 above 4")

    def _toy(n_sinks: int, *, clk: bool = False) -> dict[str, Any]:
        cells: dict[str, Any] = {
            "drv": {
                "hide_name": 0,
                "type": "sky130_fd_sc_hd__inv_2",
                "connections": {"A": [2], "Y": [3]},
            }
        }
        ports = {
            "a": {"direction": "input", "bits": [2]},
            "y": {"direction": "output", "bits": list(range(4, 4 + n_sinks))},
        }
        if clk:
            ports["core_clk"] = {"direction": "input", "bits": [3]}
            cells["drv"]["connections"]["Y"] = [99]
        for i in range(n_sinks):
            src = 3 if not clk else 3  # clock port bit when clk
            if clk:
                src = 3
            cells[f"s{i}"] = {
                "hide_name": 0,
                "type": "sky130_fd_sc_hd__inv_2",
                "connections": {"A": [src], "Y": [4 + i]},
            }
        nets = {p: {"hide_name": 0, "bits": ports[p]["bits"]} for p in ports}
        if not clk:
            nets["n_hot"] = {"hide_name": 1, "bits": [3]}
        return {
            "ports": ports,
            "cells": cells,
            "netnames": nets,
        }

    toy = _toy(20)
    before = analyze_design({"modules": {"t": json.loads(json.dumps(toy))}})
    expect(before["max_fanout_before"] >= 20, f"toy fanout {before}")
    t1 = json.loads(json.dumps(toy))
    t2 = json.loads(json.dumps(toy))
    r1 = buffer_module(t1, 16)
    r2 = buffer_module(t2, 16)
    expect(r1["n_bufs"] > 0, f"inserted bufs {r1}")
    expect(r1["max_fanout_after"] <= 16, f"after {r1}")
    expect(t1 == t2 and r1 == r2, "buffer_module is deterministic")
    clk_mod = _toy(20, clk=True)
    rclk = buffer_module(clk_mod, 16)
    expect(
        rclk["n_bufs"] == 0 and rclk["max_fanout_after"] >= 20,
        f"clock net not buffered {rclk}",
    )
    if shutil.which("yosys"):
        with tempfile.TemporaryDirectory() as td:
            jp = Path(td) / "t.json"
            outp = Path(td) / "t2.json"
            jp.write_text(
                json.dumps({"creator": "qs-self-check", "modules": {"t": t1}}),
                encoding="utf-8",
            )
            outp.write_text(
                json.dumps({"creator": "qs-self-check", "modules": {"t": t1}}),
                encoding="utf-8",
            )
            cp = run(
                [
                    "yosys",
                    "-p",
                    f"read_json {outp}; hierarchy -top t; "
                    f"write_verilog -noattr -noexpr {Path(td) / 't.v'}",
                ]
            )
            expect(
                cp.returncode == 0,
                f"buffered json not readable by yosys:\n"
                f"{(cp.stdout or '')[-300:]}",
            )
            tv = Path(td) / "t.v"
            if tv.is_file():
                body = tv.read_text(encoding="utf-8")
                expect(
                    "sky130_fd_sc_hd__buf_" in body,
                    "emitted verilog has buf cells",
                )
            else:
                expect(False, "yosys did not write buffered verilog")

    with tempfile.TemporaryDirectory() as td:
        tree = Path(td)
        (tree / "rtl" / "common").mkdir(parents=True)
        dirs, warn = yosys_incdirs(tree)
        expect(
            warn is not None and "rtl/common" in (warn or ""),
            f"fallback warn {warn}",
        )
        expect(any(p.name == "common" for p in dirs), f"fallback dirs {dirs}")

    if failures:
        print("self-check FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("self-check OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Impl quick-synth (Sky130 hd tt proxy)")
    ap.add_argument("--repo", type=Path, default=REPO_DEFAULT)
    ap.add_argument("--ref", help="git ref to synthesize (archive to a temp tree)")
    ap.add_argument("--work-tree", type=Path, help="existing tree (skip git archive)")
    ap.add_argument("--base", default="origin/main", help="diff base for default tops")
    ap.add_argument("--tops", help="comma-separated top module names")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--liberty", type=Path, default=None)
    ap.add_argument(
        "--chparam",
        action="append",
        default=[],
        help="optional override KEY=VAL or TOP:KEY=VAL (SPEC §2.2 has no required chparam)",
    )
    ap.add_argument(
        "--baseline-json",
        type=Path,
        help="prior results.json for QoR compare",
    )
    ap.add_argument(
        "--baseline-report",
        type=Path,
        help="prior quick-synth markdown report for QoR compare",
    )
    ap.add_argument(
        "--baseline-map",
        action="append",
        default=[],
        help="NEW=OLD or NEW=OLD:VARIANT (e.g. ub_pcs_lane_dist_x4=ub_pcs_lane_dist:PRODUCT)",
    )
    ap.add_argument(
        "--sram-bit-threshold",
        type=int,
        default=int(os.environ.get("QS_SRAM_BIT_THRESHOLD", DEFAULT_SRAM_BIT_THRESHOLD)),
        help=(
            f"blackbox ub_cmn_mem_1r1w (and blackbox.yml) instances whose "
            f"depth×width exceeds this many bits (default {DEFAULT_SRAM_BIT_THRESHOLD})"
        ),
    )
    ap.add_argument(
        "--incdir",
        action="append",
        default=[],
        help="extra Yosys -I directory (repeatable; default is rtl/pyc_lib)",
    )
    ap.add_argument(
        "--no-buffer",
        action="store_true",
        default=os.environ.get("QS_NO_BUFFER") == "1",
        help="skip post-map fanout buffering (default: buffer ON)",
    )
    ap.add_argument(
        "--max-fanout",
        type=int,
        default=int(os.environ.get("QS_MAX_FANOUT", DEFAULT_MAX_FANOUT)),
        help=f"max sinks per driver after buffering (default {DEFAULT_MAX_FANOUT})",
    )
    ap.add_argument(
        "--json",
        type=Path,
        help="write machine-readable results (default: <out>/results.json)",
    )
    ap.add_argument(
        "--self-check",
        action="store_true",
        help="run parser/mapping unit checks and exit (no synth)",
    )
    args = ap.parse_args(argv)

    if args.self_check:
        return self_check()

    if args.out is None:
        die("--out is required (unless --self-check)")

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

    ch_global: dict[str, str] = {}
    ch_per: dict[str, dict[str, str]] = {}
    for spec in args.chparam:
        top, key, val = parse_chparam_arg(spec)
        if top is None:
            ch_global[key] = val
        else:
            ch_per.setdefault(top, {})[key] = val

    maps: dict[str, tuple[str, str | None]] = {}
    for spec in args.baseline_map:
        new, old, var = parse_baseline_map_arg(spec)
        maps[new] = (old, var)

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

        extra_incdirs = list(parse_incdirs_env(os.environ.get("QS_INCDIRS")))
        extra_incdirs.extend(Path(p) for p in args.incdir)
        incdirs, inc_warn = yosys_incdirs(tree, extra_incdirs)
        if inc_warn:
            print(inc_warn, flush=True)

        leaves = list_rtl_leaves(tree)
        if args.tops:
            tops = [t.strip() for t in args.tops.split(",") if t.strip()]
        else:
            tops = default_tops(repo, tree, args.base, args.ref or head_sha)
        deleted_rows: list[dict[str, Any]] = []
        live_tops: list[str] = []
        for top in tops:
            if is_library_cell(top):
                print(f"==> {top} library cell (not a reported top)", flush=True)
                continue
            if is_to_be_deleted(top):
                rec = leaves.get(top) or {}
                srcp = rec.get("product") or rec.get("hooks")
                src_s = ""
                if srcp:
                    src_s = (
                        str(srcp.relative_to(tree))
                        if srcp.is_relative_to(tree)
                        else str(srcp)
                    )
                print(f"==> {top} 待删除 / to be deleted (not synthesized)", flush=True)
                deleted_rows.append(
                    {
                        "top": top,
                        "variant": "待删除 / to be deleted",
                        "ok": True,
                        "to_be_deleted": True,
                        "src": src_s,
                        "notes": [
                            "legacy; excluded from PRODUCT totals and baseline compare"
                        ],
                        "anomalies": [],
                        "delta_vs_baseline": "excluded (to be deleted)",
                        "qor_over_10pct": [],
                        "sram_est_um2": 0.0,
                    }
                )
            else:
                live_tops.append(top)
        if not live_tops and not deleted_rows:
            die("no tops to synthesize (pass --tops or touch rtl/<block>/ leaves)")

        bb_yml = tree / "scripts" / "gate" / "blackbox.yml"
        if not bb_yml.is_file():
            bb_yml = repo / "scripts" / "gate" / "blackbox.yml"
        bb_entries = load_blackbox_yml(bb_yml) if bb_yml.is_file() else []
        mem_catalog = build_mem_catalog(tree, args.sram_bit_threshold, bb_entries)

        versions = tool_versions(liberty, liberty_meta)
        jobs: list[tuple[str, str, Path, dict[str, str] | None]] = []
        for top in live_tops:
            rec = leaves.get(top)
            if not rec or ("product" not in rec and "hooks" not in rec):
                jobs.append((top, "PRODUCT", Path(), None))
                continue
            override = dict(ch_global)
            override.update(ch_per.get(top, {}))
            extra = override or None
            if "product" in rec:
                jobs.append((top, "PRODUCT", rec["product"], extra))
            if "hooks" in rec:
                jobs.append((top, "HOOKS", rec["hooks"], extra))

        results: list[dict[str, Any]] = list(deleted_rows)
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
                        "placeholder": is_placeholder_name(top),
                        "sram_est_um2": 0.0,
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
                chparam_override=extra,
                period_ns=period_ns,
                variant=variant,
                mem_catalog=mem_catalog,
                sram_bit_threshold=args.sram_bit_threshold,
                extra_incdirs=extra_incdirs,
                buffer=not args.no_buffer,
                max_fanout_limit=args.max_fanout,
            )
            results.append(r)

        baseline_rows: list[dict[str, Any]] = []
        if args.baseline_json or args.baseline_report:
            baseline_rows = load_baseline_rows(args.baseline_json, args.baseline_report)
        for r in results:
            if r.get("to_be_deleted") or is_to_be_deleted(r.get("top") or ""):
                r["delta_vs_baseline"] = "excluded (to be deleted)"
                r["qor_over_10pct"] = []
                continue
            if not baseline_rows:
                r.setdefault("delta_vs_baseline", "new")
                r.setdefault("qor_over_10pct", [])
                continue
            old, how = resolve_baseline(
                r.get("top") or "", r.get("variant") or "PRODUCT", baseline_rows, maps
            )
            if old is None:
                r["delta_vs_baseline"] = "new"
                r["qor_over_10pct"] = []
                r["baseline_how"] = how
                continue
            cmpd = qor_compare(r, old)
            r["delta_vs_baseline"] = f"{cmpd['delta_vs_baseline']} [{how}]"
            r["qor_over_10pct"] = cmpd["qor_over_10pct"]
            r["baseline_how"] = how
            r["baseline_ref"] = {
                "top": old.get("top"),
                "variant": old.get("variant"),
            }

        payload = {
            "head_sha": head_sha,
            "base": args.base,
            "period_ns": period_ns,
            "period_source": period_src,
            "period_placeholder": period_ph,
            "sram_bit_threshold": args.sram_bit_threshold,
            "sram_formula": SRAM_FORMULA_LABEL,
            "sram_um2_per_bit": SRAM_UM2_PER_BIT,
            "sram_periph_factor": SRAM_PERIPH_FACTOR,
            "tools": versions,
            "incdirs": [str(p) for p in incdirs],
            "incdir_warn": inc_warn,
            "buffer": not args.no_buffer,
            "max_fanout_limit": args.max_fanout,
            "buffer_method": (
                "yosys_buf_tree" if not args.no_buffer else "none"
            ),
            "product_totals": product_area_totals(results),
            "results": results,
        }
        jpath = args.json or (out / "results.json")
        jpath.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(write_full_markdown(results, inc_warn=inc_warn))
        print(f"\nSRAM formula: {SRAM_FORMULA_LABEL}")
        print(f"JSON: {jpath}")
        return 0 if all(r.get("ok") for r in results) else 1
    finally:
        if cleanup is not None:
            shutil.rmtree(cleanup, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
