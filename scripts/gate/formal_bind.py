#!/usr/bin/env python3
"""Every signal bound in formal/**/*.sby (and its assertion files) must exist.

Looks at bind port maps. The corresponding netlist is the bind-target module
file listed in the .sby (prefer rtl/, including hooks/). A missing netlist or
missing signal is blocking.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
    Finding,
    REPO_ROOT,
    RTL_SOURCE_SUFFIXES,
    emit_report,
    parse_ports,
    print_tool_versions,
    rel,
    strip_verilog_comments,
)

BIND_RE = re.compile(
    r"\bbind\s+([A-Za-z_][A-Za-z0-9_]*)\s+"
    r"(?:[A-Za-z_][A-Za-z0-9_]*\s+)?"
    r"(?:[A-Za-z_][A-Za-z0-9_]*\s*)?"
    r"\((.*?)\)\s*;",
    re.S,
)
PORTMAP_RE = re.compile(
    r"\.([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*([^)]+?)\s*\)",
)
IDENT_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
WIRE_RE = re.compile(
    r"\b(?:wire|reg|logic|input|output|inout)\b[^;\n]*?\b([A-Za-z_][A-Za-z0-9_]*)\s*[;,=)]",
    re.I,
)
SBY_FILE_RE = re.compile(
    r"(?:^|\s)(?:read(?:_verilog)?|read\s+-sv)\s+(\S+)",
    re.I,
)
LITERAL_RE = re.compile(r"^(\d+'[sS]?[bBhHdD][0-9a-fA-FxXzZ_]+|\d+)$")


def sby_listed_paths(sby_path: Path, repo_root: Path) -> list[Path]:
    text = sby_path.read_text(encoding="utf-8", errors="replace")
    listed: list[Path] = []
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].split()[0].lower()
            continue
        if not line or line.startswith("#"):
            continue
        candidates: list[str] = []
        if section == "files":
            candidates.append(line.split()[0])
        for m in SBY_FILE_RE.finditer(line):
            candidates.append(m.group(1))
        for token in candidates:
            token = token.strip("\"'")
            path = Path(token)
            if not path.is_absolute():
                path = (repo_root / token).resolve() if (repo_root / token).exists() else (
                    sby_path.parent / token
                ).resolve()
            if path.is_file():
                listed.append(path)
    # Also accept sibling assertion files referenced by name only.
    for m in re.finditer(r"([A-Za-z0-9_./-]+\.(?:sv|v|svh|vh))", text):
        token = m.group(1)
        for base in (repo_root, sby_path.parent):
            cand = (base / token).resolve()
            if cand.is_file():
                listed.append(cand)
    # unique, stable
    seen: set[Path] = set()
    out: list[Path] = []
    for p in listed:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        out.append(rp)
    return out


def extract_bind_signals(text: str) -> list[tuple[str, list[str]]]:
    """Return (target_module, [netlist signal names]) from bind statements."""
    clean = strip_verilog_comments(text)
    out: list[tuple[str, list[str]]] = []
    for m in BIND_RE.finditer(clean):
        module = m.group(1)
        body = m.group(2)
        signals: list[str] = []
        for pm in PORTMAP_RE.finditer(body):
            rhs = pm.group(2).strip()
            if LITERAL_RE.match(rhs.replace(" ", "")):
                continue
            for ident in IDENT_RE.findall(rhs):
                if ident.lower() in {
                    "input",
                    "output",
                    "inout",
                    "wire",
                    "reg",
                    "logic",
                    "signed",
                }:
                    continue
                signals.append(ident)
        out.append((module, signals))
    return out


def netlist_identifiers(path: Path) -> set[str]:
    names = {n for _d, n in parse_ports(path)}
    text = strip_verilog_comments(path.read_text(encoding="utf-8", errors="replace"))
    for m in WIRE_RE.finditer(text):
        names.add(m.group(1))
    return names


def find_netlist_for_module(
    module: str, listed: list[Path], repo_root: Path
) -> Path | None:
    rtl_hits = [
        p
        for p in listed
        if p.stem == module and p.suffix.lower() in RTL_SOURCE_SUFFIXES
    ]
    if rtl_hits:
        hooks = [p for p in rtl_hits if "hooks" in {x.lower() for x in p.parts}]
        return hooks[0] if hooks else rtl_hits[0]
    rtl = repo_root / "rtl"
    if not rtl.is_dir():
        return None
    found = [
        p
        for p in rtl.rglob("*")
        if p.is_file()
        and p.stem == module
        and p.suffix.lower() in RTL_SOURCE_SUFFIXES
    ]
    if not found:
        return None
    hooks = [p for p in found if "hooks" in {x.lower() for x in p.parts}]
    return hooks[0] if hooks else found[0]


def check_formal_binds(repo_root: Path, check: str = "formal") -> list[Finding]:
    findings: list[Finding] = []
    formal = repo_root / "formal"
    if not formal.is_dir():
        return findings
    sby_files = sorted(formal.rglob("*.sby"))
    for sby in sby_files:
        listed = sby_listed_paths(sby, repo_root)
        sources = [p for p in listed if p.suffix.lower() in {".sv", ".v", ".svh"}]
        if sby not in sources:
            sources.append(sby)
        binds: list[tuple[str, list[str], Path]] = []
        for src in sources:
            try:
                text = src.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for module, signals in extract_bind_signals(text):
                binds.append((module, signals, src))
        if not binds:
            continue
        for module, signals, src in binds:
            netlist = find_netlist_for_module(module, listed, repo_root)
            if netlist is None:
                findings.append(
                    Finding(
                        check=check,
                        module=module,
                        file=rel(sby),
                        rule="BIND_NETLIST_MISSING",
                        message=(
                            f"{rel(src)} binds {module} but no matching netlist "
                            f"was found for {sby.relative_to(repo_root).as_posix()}"
                        ),
                    )
                )
                continue
            present = netlist_identifiers(netlist)
            missing = [s for s in signals if s not in present]
            if missing:
                findings.append(
                    Finding(
                        check=check,
                        module=module,
                        file=rel(sby),
                        rule="BIND_SIGNAL_MISSING",
                        message=(
                            f"bound signal(s) {missing} not in {rel(netlist)} "
                            f"(from {rel(src)})"
                        ),
                    )
                )
    return findings


def main() -> int:
    print_tool_versions(["python", "sby", "yosys"])
    findings = check_formal_binds(REPO_ROOT)
    n_sby = len(list((REPO_ROOT / "formal").rglob("*.sby"))) if (
        REPO_ROOT / "formal"
    ).is_dir() else 0
    print(f"formal bind-existence: {n_sby} .sby file(s), {len(findings)} finding(s)")
    return emit_report("formal", findings)


if __name__ == "__main__":
    raise SystemExit(main())
