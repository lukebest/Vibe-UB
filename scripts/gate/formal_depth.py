"""GATE-FORMAL-DEPTH (3): bmc depth >= deepest reachable cover step + 6.

Report-only. Parses the .sby BMC depth and cover-engine log traces
left by `sby` next to formal/<iface>/*.sby.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from formal_bind import discover_sby_files
from gatelib import Finding, REPO_ROOT, emit_report, rel

COVER_MARGIN = 6
COVER_STEP_RE = re.compile(
    r"Reached cover statement\b.*?(?:\((?:step|depth)\s+(\d+)\)|"
    r"at\s+depth\s+(\d+)|step\s+(\d+))",
    re.I | re.S,
)
COVER_ALT_RE = re.compile(
    r"Cover reached\b.*?(?:step|depth)\s+(\d+)",
    re.I | re.S,
)


def parse_sby_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = ""
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("[") and s.endswith("]") and len(s) > 2:
            current = s[1:-1].strip().lower()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(raw)
    return sections


def parse_sby_bmc_depth(text: str) -> int | None:
    """Task-specific `bmc: depth N` wins; else unprefixed `depth N`."""
    bmc: int | None = None
    generic: int | None = None
    for raw in parse_sby_sections(text).get("options", []):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        prefix = ""
        rest = line
        if ":" in line:
            left, right = line.split(":", 1)
            if left.strip() and " " not in left.strip():
                prefix = left.strip().lower()
                rest = right.strip()
        parts = rest.split()
        if len(parts) < 2 or parts[0] != "depth":
            continue
        try:
            n = int(parts[1])
        except ValueError:
            continue
        if prefix == "bmc" or prefix.endswith("_bmc"):
            bmc = n
        elif prefix == "":
            generic = n
    return bmc if bmc is not None else generic


def cover_steps_in_text(text: str) -> list[int]:
    steps: list[int] = []
    for m in COVER_STEP_RE.finditer(text):
        for g in m.groups():
            if g is not None:
                steps.append(int(g))
                break
    for m in COVER_ALT_RE.finditer(text):
        steps.append(int(m.group(1)))
    return steps


def cover_workdirs(sby_path: Path) -> list[Path]:
    stem = sby_path.stem
    parent = sby_path.parent
    if not parent.is_dir():
        return []
    out: list[Path] = []
    for child in sorted(parent.iterdir()):
        if not child.is_dir() or child.is_symlink():
            continue
        name = child.name
        if name == f"{stem}_cover" or (
            name.startswith(f"{stem}_") and name.endswith("_cover")
        ):
            out.append(child)
    return out


def deepest_cover_step(cover_dir: Path) -> int | None:
    steps: list[int] = []
    for path in cover_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {"", ".txt", ".log", ".status", ".sby"}:
            if path.name not in {"logfile", "status", "logfile.txt"}:
                continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        steps.extend(cover_steps_in_text(text))
    return max(steps) if steps else None


def check_formal_depth(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for sby in discover_sby_files(root):
        try:
            text = sby.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        bmc = parse_sby_bmc_depth(text)
        if bmc is None:
            continue
        cover_max: int | None = None
        for cdir in cover_workdirs(sby):
            step = deepest_cover_step(cdir)
            if step is None:
                continue
            cover_max = step if cover_max is None else max(cover_max, step)
        if cover_max is None:
            continue
        need = cover_max + COVER_MARGIN
        if bmc >= need:
            continue
        try:
            file_rel = sby.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            file_rel = rel(sby)
        findings.append(
            Finding(
                check="formal",
                module=sby.stem,
                file=file_rel,
                rule="FORMAL_BMC_SHALLOW",
                message=(
                    f"bmc depth {bmc} < deepest cover step {cover_max} + "
                    f"{COVER_MARGIN} (need >= {need})"
                ),
                bucket="report",
                severity="warning",
            )
        )
    return findings


def main() -> int:
    findings = check_formal_depth(REPO_ROOT)
    print(
        f"formal depth: {len(discover_sby_files(REPO_ROOT))} .sby, "
        f"{len(findings)} FORMAL_BMC_SHALLOW (report-only)"
    )
    return emit_report("formal_depth", findings)


if __name__ == "__main__":
    raise SystemExit(main())
