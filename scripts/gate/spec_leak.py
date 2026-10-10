#!/usr/bin/env python3
"""spec-leak: private spec material must not enter the public repo.

Forbidden (any file, including the PR diff vs origin/main):
  strings: vibe-ub-spec-private, /workspace/vibe-ub-c/, /workspace/vibe-ub-b/,
           /workspace/ubpdf/, ch9_fields, spec-answers, ch9-answers,
           ch9-figure-resolution, decision-table, .pre-pdf.yaml,
           confidence: pdf
  marker:  GENERATED FROM ch9_fields
  name:    fmt.py, .pre-pdf.yaml
  files:   *.pdf
  images:  committed PNG/JPG outside docs/, or name contains page / ubpdf

Allowlist: scripts/gate/leak_allow.yml (gatekeeper approver required).
This script and docs/rules/verif_gate.md must be on that list.
"""

from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
    REPO_ROOT,
    Finding,
    emit_report,
    is_leak_allowed,
    load_leak_allow,
    rel,
    run_cmd,
)

# Patterns are listed in verif_gate.md §1.3. Both files are allowlisted.
LEAK_STRINGS = (
    "vibe-ub-spec-private",
    "/workspace/vibe-ub-c/",
    "/workspace/vibe-ub-b/",
    "/workspace/ubpdf/",
    "ch9_fields",
    "spec-answers",
    "ch9-answers",
    "ch9-figure-resolution",
    "decision-table",
    ".pre-pdf.yaml",
    "confidence: pdf",
    "GENERATED FROM ch9_fields",
)
PDF_GLOB = "*.pdf"
FORBIDDEN_NAMES = {"fmt.py", ".pre-pdf.yaml"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
IMAGE_NAME_NEEDLES = ("page", "ubpdf")
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    ".pycircuit-src",
    ".pycircuit_out",
    ".pycircuit-venv",
    "__pycache__",
    "node_modules",
    "out",
    "sim_build",
}
MAX_READ = 2_000_000


def _skip_dir(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def iter_repo_files() -> list[Path]:
    """Tracked files plus non-ignored untracked files."""
    seen: set[Path] = set()
    out: list[Path] = []

    def add(raw: str) -> None:
        if not raw or raw.endswith("/"):
            return
        path = Path(raw)
        if not path.is_absolute():
            path = (REPO_ROOT / raw)
        try:
            path = path.resolve()
            rel_p = path.relative_to(REPO_ROOT.resolve())
        except (OSError, ValueError):
            return
        if not path.is_file() or _skip_dir(rel_p):
            return
        if path in seen:
            return
        seen.add(path)
        out.append(path)

    tracked = run_cmd(["git", "ls-files", "-z"])
    for raw in (tracked.stdout or "").split("\0"):
        add(raw)
    extra = run_cmd(["git", "ls-files", "-z", "--others", "--exclude-standard"])
    for raw in (extra.stdout or "").split("\0"):
        add(raw)
    return sorted(out)


def scan_text(text: str) -> list[str]:
    hits = [p for p in LEAK_STRINGS if p in text]
    return hits


def image_findings(path: Path, rel_path: str) -> list[Finding]:
    """Committed PNG/JPG outside docs/, or name contains page/ubpdf."""
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        return []
    name_l = path.name.lower()
    parts = Path(rel_path).parts
    outside_docs = not parts or parts[0] != "docs"
    name_hit = any(n in name_l for n in IMAGE_NAME_NEEDLES)
    if not (outside_docs or name_hit):
        return []
    why = []
    if outside_docs:
        why.append("outside docs/")
    if name_hit:
        why.append("filename contains page/ubpdf")
    return [
        Finding(
            check="spec_leak",
            module="*",
            file=rel_path,
            rule="LEAK_IMAGE",
            message="committed PNG/JPG is not allowed (" + "; ".join(why) + ")",
        )
    ]


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    name = path.name
    rel_path = rel(path)
    if is_leak_allowed(path):
        return findings
    if fnmatch.fnmatch(name.lower(), PDF_GLOB) or path.suffix.lower() == ".pdf":
        findings.append(
            Finding(
                check="spec_leak",
                module="*",
                file=rel_path,
                rule="LEAK_PDF",
                message="PDF must not be committed to the public repo",
            )
        )
    if name in FORBIDDEN_NAMES:
        findings.append(
            Finding(
                check="spec_leak",
                module="*",
                file=rel_path,
                rule="LEAK_FILENAME",
                message=f"forbidden filename {name}",
            )
        )
    findings.extend(image_findings(path, rel_path))
    try:
        data = path.read_bytes()[:MAX_READ]
    except OSError:
        return findings
    if b"\0" in data[:1024] and path.suffix.lower() != ".pdf":
        return findings
    text = data.decode("utf-8", errors="replace")
    for pat in scan_text(text):
        findings.append(
            Finding(
                check="spec_leak",
                module="*",
                file=rel_path,
                rule="LEAK_STRING",
                message=f"private-spec token {pat!r} in file",
            )
        )
    return findings


def scan_pr_diff() -> list[Finding]:
    """Also scan the PR diff vs origin/main (added/changed lines)."""
    findings: list[Finding] = []
    proc = run_cmd(["git", "rev-parse", "--verify", "origin/main"])
    if proc.returncode != 0:
        print("NOTE: origin/main missing; skip PR-diff leak scan")
        return findings
    diff = run_cmd(["git", "diff", "-U0", "origin/main...HEAD"])
    text = diff.stdout or ""
    if not text.strip():
        print("PR diff vs origin/main: empty or identical")
        return findings
    # Attribute hits to the +++ path when possible.
    current = "PR_DIFF"
    for line in text.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            if not is_leak_allowed(REPO_ROOT / current):
                findings.extend(image_findings(Path(current), current))
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        body = line[1:]
        if is_leak_allowed(REPO_ROOT / current):
            continue
        for pat in scan_text(body):
            findings.append(
                Finding(
                    check="spec_leak",
                    module="*",
                    file=current,
                    rule="LEAK_STRING",
                    message=f"private-spec token {pat!r} in PR diff vs origin/main",
                )
            )
    return findings


def main() -> int:
    allow = load_leak_allow()
    print(f"leak allowlist: {len(allow)} approved path(s)")
    for entry in allow:
        print(f"  allow {entry.get('file') or entry.get('path')}")
    files = iter_repo_files()
    print(f"spec-leak scan: {len(files)} file(s)")
    findings: list[Finding] = []
    for path in files:
        findings.extend(scan_file(path))
    findings.extend(scan_pr_diff())
    # Dedup
    seen: set[tuple] = set()
    uniq: list[Finding] = []
    for f in findings:
        key = (f.file, f.rule, f.message)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)
    return emit_report("spec_leak", uniq)


if __name__ == "__main__":
    raise SystemExit(main())
