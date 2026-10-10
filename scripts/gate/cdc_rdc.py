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
    blackbox_by_module,
    discover_rtl,
    emit_report,
    handwritten_modules,
    is_cmn_mem_module,
    is_placeholder_module,
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
    r"\b(input|output|inout)\b((?:\s+(?:wire|reg|logic|signed))*"
    r"(?:\s+\[[^\]]+\])?\s*"
    r"[A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)",
    re.I,
)
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
INST_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\s+(?:#\s*\([^;]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(",
)
ARRAY_DECL_RE = re.compile(
    r"\b(?:reg|logic)\b(?:\s+\[[^\]]+\])?\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[",
    re.I,
)


def load_rules() -> dict:
    return load_yaml(CDC_RULES)


def _decl_idents(blob: str) -> list[str]:
    skip = {"input", "output", "inout", "wire", "reg", "logic", "signed"}
    return [t for t in IDENT_RE.findall(blob) if t.lower() not in skip]


def port_names(mod_text: str, regex: str) -> list[str]:
    cre = re.compile(regex)
    names: list[str] = []
    for _kind, blob in PORT_RE.findall(mod_text):
        for name in _decl_idents(blob):
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
    whitelist |= handwritten_modules()
    rst_sync = (rules.get("rst_sync") or {}).get("cell") or "ub_rst_sync"
    sync_cells = {row["name"] for row in (rules.get("sync_cells") or []) if row.get("name")}
    sync_cells |= handwritten_modules()
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
    if is_cmn_mem_module(name) and "core_clk" not in clocks:
        findings.append(
            Finding(
                check="cdc",
                module=name,
                file=file,
                rule="CMN_MEM_CLK",
                message="ub_cmn_mem_1r1w clock port must be core_clk (Xia)",
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
    if has_rst_n and name != rst_sync and name not in whitelist:
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
    for _kind, blob in PORT_RE.findall(text):
        for pname in _decl_idents(blob):
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


def rdc_unreset_arrays(name: str, file: str, text: str) -> list[Finding]:
    """Array writes without reset require blackbox.yml valid_outside: true."""
    arrays = ARRAY_DECL_RE.findall(text)
    if not arrays:
        return []
    written = set()
    reset_assigned = set()
    for m in ALWAYS_ASYNC_RE.finditer(text):
        # body is approximate: from this always to the next always/endmodule
        start = m.end()
        nxt = re.search(r"\balways\b|\bendmodule\b", text[start:], re.I)
        body = text[start : start + (nxt.start() if nxt else len(text))]
        async_rsts = async_reset_edges(m.group(1))
        for arr in arrays:
            if re.search(rf"\b{re.escape(arr)}\s*\[", body):
                written.add(arr)
                if async_rsts and re.search(
                    rf"\b{re.escape(arr)}\b.?(?:<=|=)", body.split("else")[0]
                ):
                    reset_assigned.add(arr)
    unreset = [a for a in arrays if a in written and a not in reset_assigned]
    if not unreset:
        return []
    entry = blackbox_by_module().get(name) or {}
    if entry.get("valid_outside") is True:
        return []
    return [
        Finding(
            check="cdc",
            module=name,
            file=file,
            rule="RDC_UNRESET_ARRAY",
            message=(
                f"array(s) {unreset} are written without reset; "
                f"register the module in scripts/gate/blackbox.yml with "
                f"valid_outside: true (C-line RDC)"
            ),
        )
    ]


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
        if is_placeholder_module(unit.module):
            print(f"cdc-rdc skip {unit.module}: _placeholder (lint/TB only)")
            continue
        raw = unit.file.read_text(encoding="utf-8", errors="replace")
        text = strip_verilog_comments(raw)
        # Analyze just this module body when the file has one module.
        bodies = MODULE_RE.findall(text)
        if not bodies:
            findings.extend(analyze_module(unit.module, unit.file, text, rules))
            findings.extend(rdc_unreset_arrays(unit.module, rel(unit.file), text))
            continue
        for mname, body in bodies:
            if mname != unit.module:
                continue
            findings.extend(analyze_module(mname, unit.file, body, rules))
            findings.extend(rdc_unreset_arrays(mname, rel(unit.file), body))
    return emit_report("cdc", findings)


if __name__ == "__main__":
    raise SystemExit(main())
