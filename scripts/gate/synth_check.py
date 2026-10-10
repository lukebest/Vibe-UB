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
    blackbox_lib_files,
    cmn_mem_bits,
    cmn_mem_is_large,
    cmn_mem_tag_of,
    discover_rtl,
    emit_report,
    is_cmn_mem_module,
    is_placeholder_path,
    large_cmn_mem_lib_files,
    parse_cmn_mem_tag,
    print_tool_versions,
    read_cmn_mem_threshold_bits,
    rel,
    run_cmd,
    shutil_which,
    stub_modules,
    yosys_inc_prefix,
    module_closure,
)

# HOOKS netlists are lint/CDC only (CODING_STYLE §1). Synth-check is PRODUCT.
HOOKS_DIR_PARTS = {"hooks", "hooks1"}


def is_product(path: Path) -> bool:
    if is_placeholder_path(path):
        return False
    parts = {p.lower() for p in path.parts}
    return not (parts & HOOKS_DIR_PARTS)


# Handwritten-list async-reset FFs (ub_rst_sync / $adff family). Not latches.
_ASYNC_FF_CELL = re.compile(
    r"\$(?:adff|adffe|dffsr|dffsre)\b|\$_DFF_(?:PN|NP)|_DFFSR_",
    re.I,
)
# Real latches only. Do not match $adff / select-command text / $_DFF_PN0_.
_LATCH_STAT = re.compile(
    r"^\s+(\$(?:dlatch|adlatch|dlatchsr)\b|\$_DLATCH\S*)\s+\d+\s*$",
    re.I,
)
_LATCH_INFERRED = re.compile(r"^Latch inferred for signal\b", re.I)
_COMBO_LOOP_HIT = re.compile(
    r"Warning:\s+found logic loop|"
    r"combinational loop|"
    r"Found an SCC:|"
    r"Found [1-9]\d* SCCs\b",
    re.I,
)
_MULTI_DRIVE = re.compile(r"multiple conflicting drivers|multiple drivers", re.I)


def parse_yosys(text: str, module: str, file: str) -> list[Finding]:
    """Parse Yosys synth-check log. Async-reset FFs are not LATCH / COMBO_LOOP.

    Handwritten.yml cells ($adff / $adffe / $dffsr, mapped $_DFF_PN0_) stay
    flops. Classify by cell type — do not skip the whole module. Ignore the
    `select -list t:$dlatch …` command echo and the
    `Executing SCC pass (detecting logic loops)` banner.
    """
    findings: list[Finding] = []
    latch_cells: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if _ASYNC_FF_CELL.search(stripped) and not _LATCH_STAT.match(line):
            continue
        if _LATCH_STAT.match(line) or _LATCH_INFERRED.match(stripped):
            latch_cells.append(stripped)
        if _MULTI_DRIVE.search(line):
            findings.append(
                Finding(
                    check="synth",
                    module=module,
                    file=file,
                    rule="MULTI_DRIVE",
                    message=stripped,
                )
            )
        if _COMBO_LOOP_HIT.search(line):
            findings.append(
                Finding(
                    check="synth",
                    module=module,
                    file=file,
                    rule="COMBO_LOOP",
                    message=stripped,
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
                        message=stripped,
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


def combo_depth_findings(text: str, module: str, file: str) -> list[Finding]:
    """Report-only: Yosys `ltp -noff` max topological combinational depth."""
    depths: list[int] = []
    for line in text.splitlines():
        m = re.search(r"(?:length|depth)\s*=\s*(\d+)", line, re.I)
        if m:
            depths.append(int(m.group(1)))
        m2 = re.search(r"Longest topological path.*?(\d+)", line, re.I)
        if m2:
            depths.append(int(m2.group(1)))
    if not depths:
        return [
            Finding(
                check="synth",
                module=module,
                file=file,
                rule="COMBO_DEPTH",
                message="ltp -noff produced no depth (report-only)",
                bucket="report",
            )
        ]
    return [
        Finding(
            check="synth",
            module=module,
            file=file,
            rule="COMBO_DEPTH",
            message=f"max combinational depth (ltp -noff) = {max(depths)}",
            bucket="report",
        )
    ]


def synth_module(
    module: str,
    file: Path,
    sources: list[Path],
    incdirs: list[Path],
    lib_extra: list[Path] | None = None,
) -> tuple[list[Finding], str]:
    inc = yosys_inc_prefix(incdirs)
    reads: list[str] = []
    seen: set[Path] = set()
    lib_files = {p.resolve() for p in blackbox_lib_files()}
    lib_files.update(p.resolve() for p in (lib_extra or []))
    lib_files.discard(file.resolve())
    for p in [file, *sources]:
        if p.suffix.lower() not in {".v", ".sv"}:
            continue
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        flag = "-sv" if rp.suffix.lower() == ".sv" else ""
        lib = "-lib" if rp in lib_files else ""
        reads.append(f"read_verilog {flag} {lib} {inc} {rp}".replace("  ", " "))
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
            "ltp -noff",
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
    findings.extend(combo_depth_findings(text, module, rel(file)))
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
    skip = stub_modules()
    thresh = read_cmn_mem_threshold_bits()
    if skip:
        print(f"synth-check: blackbox.yml modules treated as -lib: {sorted(skip)}")
    print(f"synth-check: ub_cmn_mem_1r1w blackbox threshold={thresh} bits")
    print(
        "synth-check: variant tag d<DEPTH>w<WIDTH>[m<WMASK_W>] "
        "(e.g. d512w512m64, d64w64m16); bits=DEPTH*WIDTH; "
        f"full synth only ≤ {thresh} bits (includes d64w64m16)"
    )
    if not modules:
        print("synth-check: no PRODUCT modules; PASS")
        return emit_report("synth", [])
    for unit in modules:
        if unit.module in skip:
            print(f"synth-check skip top {unit.module}: listed in blackbox.yml (used as -lib)")
            continue
        extra = parse_cmn_mem_tag(cmn_mem_tag_of(unit.module) or "") or {
            "module": unit.module
        }
        if is_cmn_mem_module(unit.module) and cmn_mem_is_large(
            unit.file, extra, thresh=thresh
        ):
            bits = cmn_mem_bits(unit.file, extra)
            print(
                f"synth-check skip full synth {unit.module}: large ub_cmn_mem_1r1w "
                f"variant ({bits} bits > {thresh}); parents blackbox this cell"
            )
            findings.append(
                Finding(
                    check="synth",
                    module=unit.module,
                    file=rel(unit.file),
                    rule="CMN_MEM_LARGE",
                    message=(
                        f"large variant ({bits} bits > {thresh}); "
                        "full synth skipped; parents use read_verilog -lib"
                    ),
                    bucket="report",
                )
            )
            continue
        needed = module_closure(unit.module, disc) or [unit.file]
        extra_lib = large_cmn_mem_lib_files(unit.module, disc)
        if extra_lib:
            print(
                f"synth-check {unit.module}: -lib large ub_cmn_mem_1r1w "
                f"{[rel(p) for p in extra_lib]}"
            )
        f, _ = synth_module(
            unit.module, unit.file, needed, disc["incdirs"], lib_extra=extra_lib
        )
        findings.extend(f)
    return emit_report("synth", findings)


if __name__ == "__main__":
    raise SystemExit(main())
