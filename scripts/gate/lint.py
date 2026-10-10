#!/usr/bin/env python3
"""Verilator --lint-only -Wall over every discovered RTL top and leaf."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
    REPO_ROOT,
    Finding,
    collect_stub_findings,
    discover_rtl,
    emit_report,
    print_tool_versions,
    rel,
    run_cmd,
    shutil_which,
    verilator_inc_args,
    module_closure,
)

WARN_RE = re.compile(
    r"^%(Error|Warning)(?:-([A-Z0-9_]+))?:(?:\s+(\S+):(\d+):)?"
)
# %Warning-UNUSED: file.v:12:3: ...
WARN_RE2 = re.compile(
    r"^%(?P<sev>Error|Warning)(?:-(?P<rule>[A-Z0-9_]+))?:(?:\s+(?P<file>\S+):(?P<line>\d+)(?::\d+)?:)?\s*(?P<msg>.*)$"
)


def parse_verilator(text: str, module: str, default_file: str) -> list[Finding]:
    findings: list[Finding] = []
    for raw in text.splitlines():
        m = WARN_RE2.match(raw.strip())
        if not m:
            continue
        if "Exiting due to" in (m.group("msg") or ""):
            continue
        sev = "error" if m.group("sev") == "Error" else "warning"
        rule = m.group("rule") or ("ERROR" if sev == "error" else "WARNING")
        fpath = m.group("file") or default_file
        line = m.group("line")
        msg = (m.group("msg") or raw).strip()
        if line:
            msg = f"line {line}: {msg}"
        if fpath and not fpath.startswith("%"):
            try:
                fpath = rel(Path(fpath.split(":")[0]))
            except Exception:
                fpath = fpath.split(":")[0]
        findings.append(
            Finding(
                check="lint",
                module=module,
                file=fpath,
                rule=rule,
                message=msg,
                severity=sev,
            )
        )
    return findings


def lint_module(module: str, file: Path, sources: list[Path], incdirs: list[Path]) -> list[Finding]:
    argv = [
        "verilator",
        "--lint-only",
        "-Wall",
        "--top-module",
        module,
        *verilator_inc_args(incdirs),
    ]
    # Unit + discovered children only (do not feed the whole tree as sources).
    seen: set[Path] = set()
    ordered: list[Path] = []
    for p in [file, *sources]:
        if p.suffix.lower() not in {".v", ".sv"}:
            continue
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        ordered.append(rp)
    argv.extend(str(p) for p in ordered)
    proc = run_cmd(argv)
    text = proc.stdout or ""
    print(f"--- verilator --lint-only -Wall --top-module {module} ---")
    if text.strip():
        print(text.rstrip())
    findings = parse_verilator(text, module, rel(file))
    if proc.returncode != 0 and not findings:
        findings.append(
            Finding(
                check="lint",
                module=module,
                file=rel(file),
                rule="ERROR",
                message=f"verilator exited {proc.returncode} with no parsed diagnostics",
                severity="error",
            )
        )
    return findings


def main() -> int:
    print_tool_versions(["verilator", "python"])
    if not shutil_which("verilator"):
        print("ERROR: verilator is not on PATH; cannot run lint")
        return 1
    disc = discover_rtl()
    modules = disc["modules"]
    sources = disc["sources"]
    incdirs = disc["incdirs"]
    print(
        f"RTL discovery: {len(sources)} file(s), {len(modules)} module(s), "
        f"filelists={'yes' if disc['used_filelists'] else 'no (directory scan)'}"
    )
    for u in modules:
        print(f"  {u.kind:4} {u.module:24} {rel(u.file)}")
    findings: list[Finding] = collect_stub_findings("lint")
    if not modules:
        print("lint: no RTL modules discovered")
        return emit_report("lint", findings)
    # Tops and leaves both — CODING_STYLE §7 covers PRODUCT and HOOKS trees
    # when they appear under rtl/. Handwritten whitelist and registered stubs
    # still lint.
    for unit in modules:
        needed = module_closure(unit.module, disc) or [unit.file]
        findings.extend(lint_module(unit.module, unit.file, needed, incdirs))
    return emit_report("lint", findings)


if __name__ == "__main__":
    raise SystemExit(main())
