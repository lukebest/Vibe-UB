#!/usr/bin/env python3
"""Yosys pass/fail synth: no latch, no multi-drive, no combo loop. No QoR compare."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
    Finding,
    discover_rtl,
    emit_report,
    print_tool_versions,
    rel,
    run_cmd,
    shutil_which,
    yosys_inc_prefix,
    module_closure,
)

# HOOKS netlists are lint/CDC only (CODING_STYLE §1). Synth-check is PRODUCT.
HOOKS_DIR_PARTS = {"hooks", "hooks1"}


def is_product(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    return not (parts & HOOKS_DIR_PARTS)


def parse_yosys(text: str, module: str, file: str) -> list[Finding]:
    findings: list[Finding] = []
    latch_cells = []
    for line in text.splitlines():
        if re.search(r"\$dlatch|\$adlatch|\$dlatchsr", line, re.I):
            latch_cells.append(line.strip())
        if re.search(r"multiple conflicting drivers|multiple drivers", line, re.I):
            findings.append(
                Finding(
                    check="synth",
                    module=module,
                    file=file,
                    rule="MULTI_DRIVE",
                    message=line.strip(),
                )
            )
        if re.search(r"logic loop|combinational loop|found loop", line, re.I):
            findings.append(
                Finding(
                    check="synth",
                    module=module,
                    file=file,
                    rule="COMBO_LOOP",
                    message=line.strip(),
                )
            )
        if re.search(r"ERROR:", line):
            if "Can't open" in line or "syntax error" in line.lower():
                findings.append(
                    Finding(
                        check="synth",
                        module=module,
                        file=file,
                        rule="YOSYS_ERROR",
                        message=line.strip(),
                    )
                )
    if latch_cells:
        findings.append(
            Finding(
                check="synth",
                module=module,
                file=file,
                rule="LATCH",
                message="; ".join(latch_cells[:8]),
            )
        )
    return findings


def synth_module(module: str, file: Path, sources: list[Path], incdirs: list[Path]) -> tuple[list[Finding], str]:
    inc = yosys_inc_prefix(incdirs)
    reads: list[str] = []
    seen: set[Path] = set()
    for p in [file, *sources]:
        if p.suffix.lower() not in {".v", ".sv"}:
            continue
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        flag = "-sv" if rp.suffix.lower() == ".sv" else ""
        reads.append(f"read_verilog {flag} {inc} {rp}")
    # Latch / multi-drive / SCC after proc; then synth + stat (pass/fail only).
    script = "\n".join(
        [
            *reads,
            f"hierarchy -check -top {module}",
            "proc",
            "opt_clean",
            "select -list t:$dlatch t:$adlatch t:$dlatchsr",
            "check",
            "scc",
            # -noabc: structural pass/fail only. QoR ABC mapping is not a gate
            # (implementation owns scripts/impl/quick_synth.sh).
            f"synth -top {module} -noabc",
            "stat",
        ]
    )
    try:
        proc = run_cmd(["yosys", "-p", script], timeout=120)
        text = proc.stdout or ""
        rc = proc.returncode
    except subprocess.TimeoutExpired as exc:
        text = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        text += f"\nTIMEOUT after 120s on {module}"
        rc = 124
    print(f"--- yosys synth {module} ({rel(file)}) ---")
    # Keep the log readable: last 40 lines always include stat / errors.
    lines = text.strip().splitlines()
    shown = lines if len(lines) <= 60 else (["..."] + lines[-59:])
    print("\n".join(shown))
    findings = parse_yosys(text, module, rel(file))
    if rc == 124:
        findings.append(
            Finding(
                check="synth",
                module=module,
                file=rel(file),
                rule="SYNTH_TIMEOUT",
                message="yosys exceeded 120s (structural synth -noabc)",
            )
        )
    elif rc != 0 and not findings:
        findings.append(
            Finding(
                check="synth",
                module=module,
                file=rel(file),
                rule="YOSYS_ERROR",
                message=f"yosys exited {proc.returncode}",
            )
        )
    return findings, text


def main() -> int:
    print_tool_versions(["yosys", "python"])
    if not shutil_which("yosys"):
        print("ERROR: yosys is not on PATH; cannot run synth-check")
        return 1
    disc = discover_rtl()
    modules = [u for u in disc["modules"] if is_product(u.file)]
    sources = [p for p in disc["sources"] if is_product(p)]
    print(f"synth-check: {len(modules)} PRODUCT module(s) (HOOKS excluded)")
    findings: list[Finding] = []
    if not modules:
        print("synth-check: no PRODUCT modules; PASS")
        return emit_report("synth", [])
    for unit in modules:
        needed = module_closure(unit.module, disc) or [unit.file]
        f, _ = synth_module(unit.module, unit.file, needed, disc["incdirs"])
        findings.extend(f)
    return emit_report("synth", findings)


if __name__ == "__main__":
    raise SystemExit(main())
