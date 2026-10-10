#!/usr/bin/env python3
"""Structural CDC / RDC checks for the M1 single-clock core.

Rules live in cdc_rules.yml so new cells / clocks can be added without
rewriting the workflow. Failures on new leaves block; D10 legacy is report-only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
    CDC_RULES,
    Finding,
    discover_rtl,
    emit_report,
    load_yaml,
    print_tool_versions,
    rel,
    strip_verilog_comments,
)

ALWAYS_ASYNC_RE = re.compile(
    r"always\s*@\s*\(([^)]*)\)",
    re.IGNORECASE,
)
MODULE_RE = re.compile(
    r"\bmodule\s+([A-Za-z_][A-Za-z0-9_]*)\b(.*?)\bendmodule\b",
    re.S,
)
PORT_RE = re.compile(
    r"\b(input|output|inout)\b(?:\s+wire|\s+reg)?(?:\s+signed)?(?:\s+\[[^\]]+\])?\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)",
    re.I,
)
INST_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\s+(?:#\s*\([^;]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(",
)


def load_rules() -> dict:
    return load_yaml(CDC_RULES)


def port_names(mod_text: str, regex: str) -> list[str]:
    cre = re.compile(regex)
    names: list[str] = []
    for _kind, name in PORT_RE.findall(mod_text):
        if cre.search(name):
            names.append(name)
    return names


def instances(mod_text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    skip = {"module", "function", "task", "if", "for", "while", "case", "always"}
    for cell, inst in INST_RE.findall(mod_text):
        if cell.lower() in skip:
            continue
        out.append((cell, inst))
    return out


def async_reset_edges(sens: str) -> list[str]:
    hits: list[str] = []
    for m in re.finditer(r"(?:posedge|negedge)\s+([A-Za-z_][A-Za-z0-9_]*)", sens, re.I):
        hits.append(m.group(1))
    # A sensitivity list with both edge(clk) and edge(rst) is an async reset.
    clocks = [n for n in hits if re.search(r"clk|clock", n, re.I)]
    resets = [n for n in hits if n not in clocks]
    if clocks and resets:
        return resets
    if re.search(r"\bor\b", sens, re.I) and len(hits) >= 2:
        return [n for n in hits[1:]]
    return []


def analyze_module(name: str, path: Path, text: str, rules: dict) -> list[Finding]:
    findings: list[Finding] = []
    file = rel(path)
    clock_re = rules.get("clock_port_regex") or r"(^clk$|_clk$|^clock$)"
    clocks = port_names(text, clock_re)
    # Also treat bare `clk` / `core_clk` identifiers in always as clocks.
    allowed = set(rules.get("allowed_clocks") or ["core_clk"])
    forbidden = set(rules.get("forbidden_clocks") or [])
    whitelist = set(rules.get("async_reset_whitelist_cells") or [])
    rst_sync = (rules.get("rst_sync") or {}).get("cell") or "ub_rst_sync"
    sync_cells = {row["name"] for row in (rules.get("sync_cells") or []) if row.get("name")}
    async_in_res = [re.compile(p) for p in (rules.get("async_input_regex") or [])]
    insts = instances(text)
    inst_cells = {c for c, _ in insts}

    if rules.get("require_single_clock", True) and len(set(clocks)) > 1:
        findings.append(
            Finding(
                check="cdc",
                module=name,
                file=file,
                rule="CLOCK_MULTI",
                message=f"multiple clock ports: {sorted(set(clocks))}",
            )
        )
    for clk in clocks:
        if clk in forbidden:
            findings.append(
                Finding(
                    check="cdc",
                    module=name,
                    file=file,
                    rule="CLOCK_FORBIDDEN",
                    message=f"forbidden clock port {clk} (M1 is single-clock, SPEC §4.1)",
                )
            )
        elif clk not in allowed:
            findings.append(
                Finding(
                    check="cdc",
                    module=name,
                    file=file,
                    rule="CLOCK_NOT_CORE",
                    message=f"clock port {clk!r} is not core_clk",
                )
            )

    for sens_m in ALWAYS_ASYNC_RE.finditer(text):
        sens = sens_m.group(1)
        async_rsts = async_reset_edges(sens)
        if not async_rsts:
            continue
        if name not in whitelist:
            findings.append(
                Finding(
                    check="cdc",
                    module=name,
                    file=file,
                    rule="RST_ASYNC_NOT_VIA_SYNC",
                    message=(
                        f"async reset sensitivity ({sens.strip()}) outside "
                        f"{rst_sync}; business logic must use sync rst_pyc "
                        f"(CODING_STYLE §2, SPEC §4.2)"
                    ),
                )
            )

    # Chip-level rst_n must enter through ub_rst_sync when this module
    # exposes rst_n and is not the sync cell itself.
    has_rst_n = bool(port_names(text, r"^rst_n$"))
    if has_rst_n and name != rst_sync:
        if rst_sync not in inst_cells:
            # Leaf that takes rst_n as a port is an unsynchronized entry
            # unless it is purely combo (no clock) and does not reset.
            if clocks or ALWAYS_ASYNC_RE.search(text):
                findings.append(
                    Finding(
                        check="cdc",
                        module=name,
                        file=file,
                        rule="RST_SYNC_MISSING",
                        message=(
                            f"rst_n is a port but {rst_sync} is not instantiated; "
                            f"async reset entry must go through {rst_sync} "
                            f"(2-stage) then ub_pyc_rst_adapt"
                        ),
                    )
                )

    # Async / non-core_clk inputs need a 2-stage sync cell.
    for _kind, pname in PORT_RE.findall(text):
        if not any(r.search(pname) for r in async_in_res):
            continue
        if name in whitelist or name in sync_cells:
            continue
        if pname == "rst_n" and rst_sync in inst_cells:
            continue
        if not (inst_cells & sync_cells) and pname == "rst_n":
            # Already covered by RST_SYNC_MISSING; skip duplicate.
            continue
        if pname != "rst_n" and not (inst_cells & sync_cells):
            findings.append(
                Finding(
                    check="cdc",
                    module=name,
                    file=file,
                    rule="ASYNC_INPUT_UNSYNC",
                    message=(
                        f"async input {pname} is not captured by a 2-stage "
                        f"synchronizer ({sorted(sync_cells)})"
                    ),
                )
            )
    return findings


def main() -> int:
    print_tool_versions(["python", "yosys"])
    rules = load_rules()
    print(f"CDC rules schema {rules.get('schema_version')} from {rel(CDC_RULES)}")
    disc = discover_rtl()
    findings: list[Finding] = []
    if not disc["modules"]:
        print("cdc-rdc: no RTL modules; PASS")
        return emit_report("cdc", [])
    for unit in disc["modules"]:
        raw = unit.file.read_text(encoding="utf-8", errors="replace")
        text = strip_verilog_comments(raw)
        # Analyze just this module body when the file has one module.
        bodies = MODULE_RE.findall(text)
        if not bodies:
            findings.extend(analyze_module(unit.module, unit.file, text, rules))
            continue
        for mname, body in bodies:
            if mname != unit.module:
                continue
            findings.extend(analyze_module(mname, unit.file, body, rules))
    return emit_report("cdc", findings)


if __name__ == "__main__":
    raise SystemExit(main())
