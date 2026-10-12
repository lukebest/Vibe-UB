"""GATE-PRIVATE-PARENT-FREE: default sby tasks must not assume private leaf outputs.

Private leaf instances are cut: their outputs are free inputs. Parent
state-legality asserts run under those free outputs. Contract-derived
`assume` on leaf outputs is allowed only in a separately named diagnostic
task (not bmc/cover/prove / unprefixed shared files).

Report-only until #47 is on main (origin/main verif_gate.md carries
GATE-PRIVATE-PARENT-FREE), or `parent_free_required` in private_leaves.yml.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from formal_bind import discover_sby_files, resolve_sby_file_token
from formal_depth import parse_sby_sections
from gatelib import Finding, REPO_ROOT, emit_report, rel, run_cmd, strip_verilog_comments
from private_leaves import (
    discover_contract_files,
    load_private_config,
    parse_contract_file,
)

DEFAULT_TASKS = frozenset({"bmc", "cover", "prove"})
TASK_PREFIX_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$")
IDENT_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
ASSUME_START_RE = re.compile(
    r"\b(?:[A-Za-z_][A-Za-z0-9_]*\s*:\s*)?assume(?:\s+property)?\s*\(",
    re.I,
)
READ_TOKEN_RE = re.compile(
    r"(?:read\s+-sv|read_verilog)\s+(\S+)",
    re.I,
)


def parent_free_required(root: Path) -> bool:
    flag = load_private_config(root).get("parent_free_required")
    if flag is True or flag is False:
        return bool(flag)
    proc = run_cmd(
        ["git", "show", "origin/main:docs/rules/verif_gate.md"],
        cwd=root,
    )
    if proc.returncode != 0:
        return False
    return "GATE-PRIVATE-PARENT-FREE" in (proc.stdout or "")


def contract_output_ports(root: Path) -> dict[str, set[str]]:
    """leaf → output port names from docs/arch/*/contracts/ YAML."""
    out: dict[str, set[str]] = {}
    for path in discover_contract_files(root):
        data, _errs = parse_contract_file(path, root)
        if not data:
            continue
        leaf = str(data.get("leaf") or "").strip()
        if not leaf:
            continue
        names: set[str] = set()
        ports = data.get("ports")
        if isinstance(ports, list):
            for port in ports:
                if not isinstance(port, dict):
                    continue
                if port.get("dir") != "out":
                    continue
                name = str(port.get("name") or "").strip()
                if name:
                    names.add(name)
        if names:
            out[leaf] = names
    return out


def _split_task_prefix(line: str) -> tuple[str | None, str]:
    raw = line.split("#", 1)[0].strip()
    if not raw:
        return None, ""
    m = TASK_PREFIX_RE.match(raw)
    if not m:
        return None, raw
    return m.group(1).lower(), m.group(2).strip()


def sby_task_names(text: str) -> set[str]:
    names: set[str] = set()
    for raw in parse_sby_sections(text).get("tasks", []):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        names.add(line.split()[0].lower())
    return names


def _is_default_prefix(prefix: str | None, tasks: set[str]) -> bool:
    if prefix is None:
        return True
    defaults = tasks & DEFAULT_TASKS
    if defaults:
        return prefix in DEFAULT_TASKS
    return prefix not in tasks or prefix in DEFAULT_TASKS


def default_task_source_paths(sby_path: Path, root: Path) -> list[Path]:
    text = sby_path.read_text(encoding="utf-8", errors="replace")
    tasks = sby_task_names(text)
    tokens: list[str] = []
    sections = parse_sby_sections(text)
    for raw in sections.get("files", []):
        prefix, body = _split_task_prefix(raw)
        if not body or not _is_default_prefix(prefix, tasks):
            continue
        tokens.append(body.split()[0].strip("\"'"))
    for raw in sections.get("script", []):
        prefix, body = _split_task_prefix(raw)
        if not body or not _is_default_prefix(prefix, tasks):
            continue
        for m in READ_TOKEN_RE.finditer(body):
            tokens.append(m.group(1).strip("\"'"))
        parts = body.split()
        if parts and parts[0].lower() == "read" and len(parts) >= 2:
            tokens.append(parts[-1].strip("\"'"))
    paths: list[Path] = []
    seen: set[Path] = set()
    for token in tokens:
        path = resolve_sby_file_token(token, sby_path, root)
        if path is None:
            continue
        rp = path.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        paths.append(rp)
    return paths


def _take_paren(text: str, open_at: int) -> str:
    depth = 0
    for i, ch in enumerate(text[open_at:], open_at):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_at + 1 : i]
    return text[open_at + 1 :]


def assume_bodies(text: str) -> list[str]:
    clean = strip_verilog_comments(text)
    bodies: list[str] = []
    for m in ASSUME_START_RE.finditer(clean):
        open_at = clean.find("(", m.start())
        if open_at < 0:
            continue
        bodies.append(_take_paren(clean, open_at))
    return bodies


def instantiated_leaves(text: str, leaves: set[str]) -> set[str]:
    clean = strip_verilog_comments(text)
    found: set[str] = set()
    for leaf in leaves:
        pat = re.compile(
            rf"\b{re.escape(leaf)}\s+(?:#\s*\([^;]*?\))?\s*"
            rf"(?:[A-Za-z_][A-Za-z0-9_]*\s*)?(?:\[[^\]]*\]\s*)?\(",
            re.S,
        )
        for m in pat.finditer(clean):
            before = clean[: m.start()].rstrip()
            if before.endswith("module") or re.search(r"\bmodule$", before):
                continue
            if before.endswith("bind") or re.search(r"\bbind$", before):
                continue
            found.add(leaf)
    return found


def check_formal_parent_free(root: Path) -> list[Finding]:
    outs = contract_output_ports(root)
    if not outs:
        return []
    leaves = set(outs)
    bucket = "new" if parent_free_required(root) else "report"
    findings: list[Finding] = []
    for sby in discover_sby_files(root):
        sources = default_task_source_paths(sby, root)
        inst: set[str] = set()
        texts: list[tuple[Path, str]] = []
        for path in sources:
            try:
                src = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            texts.append((path, src))
            inst |= instantiated_leaves(src, leaves)
        if not inst:
            continue
        watched = {name for leaf in inst for name in outs[leaf]}
        if not watched:
            continue
        try:
            sby_rel = sby.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            sby_rel = rel(sby)
        seen: set[tuple[str, str]] = set()
        for _path, src in texts:
            for body in assume_bodies(src):
                ids = set(IDENT_RE.findall(body))
                for leaf in sorted(inst):
                    hit_ports = sorted(outs[leaf] & ids)
                    if not hit_ports:
                        continue
                    key = (leaf, hit_ports[0])
                    if key in seen:
                        continue
                    seen.add(key)
                    findings.append(
                        Finding(
                            check="formal",
                            module=sby.stem,
                            file=sby_rel,
                            rule="FORMAL_PRIVATE_ASSUME",
                            message=(
                                f"default task assumes private leaf output "
                                f"{hit_ports[0]} of {leaf}; cut the stub and "
                                "keep assume only in a named diagnostic task"
                            ),
                            bucket=bucket,
                            severity="error" if bucket == "new" else "warning",
                        )
                    )
    return findings


def main() -> int:
    findings = check_formal_parent_free(REPO_ROOT)
    print(
        f"formal parent-free: {len(discover_sby_files(REPO_ROOT))} .sby, "
        f"{len(findings)} FORMAL_PRIVATE_ASSUME "
        f"({'blocking' if parent_free_required(REPO_ROOT) else 'report-only'})"
    )
    return emit_report("formal_parent_free", findings)


if __name__ == "__main__":
    raise SystemExit(main())
