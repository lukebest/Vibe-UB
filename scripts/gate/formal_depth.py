"""GATE-FORMAL-DEPTH (3)+(4): cover margin and HOOKS→PRODUCT prove inherit.

(3) Report-only: bmc depth >= deepest reachable cover step + 6.
(4) Report-only: PRODUCT may inherit a converged HOOKS prove only when
    the same-run equiv job reports a real PASS (not SKIP/PRIVATE_SKIP)
    on all PRODUCT outputs. Else fall back to rule 2.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from formal_bind import discover_sby_files
from gatelib import Finding, OUT_DIR, REPO_ROOT, emit_report, rel

COVER_MARGIN = 6
INHERIT_STATUS = "proven via HOOKS prove + PRODUCT≡HOOKS equiv"
EQUIV_STATUS_NAME = "equiv_status.json"
DEFAULT_TASKS = frozenset({"bmc", "cover", "prove"})
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


def _sby_rel(sby: Path, root: Path) -> str:
    try:
        return sby.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return rel(sby)


def sby_task_names(text: str) -> set[str]:
    names: set[str] = set()
    for raw in parse_sby_sections(text).get("tasks", []):
        line = raw.split("#", 1)[0].strip()
        if line:
            names.add(line.split()[0].lower())
    return names


def task_option(text: str, task: str, key: str) -> str | None:
    hit: str | None = None
    generic: str | None = None
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
        if len(parts) < 2 or parts[0] != key:
            continue
        if prefix == task or prefix.endswith(f"_{task}"):
            hit = parts[1].lower()
        elif prefix == "":
            generic = parts[1].lower()
    return hit if hit is not None else generic


def is_product_prove_task(name: str, text: str) -> bool:
    if name in DEFAULT_TASKS or "product" not in name:
        return False
    mode = task_option(text, name, "mode")
    if mode == "prove":
        return True
    return mode is None and "prove" in name


def sby_inherits_hooks_prove(text: str) -> bool:
    """Default `prove` is HOOKS; a non-default `*product*` prove exists."""
    tasks = sby_task_names(text)
    if "prove" not in tasks:
        return False
    return any(is_product_prove_task(name, text) for name in tasks)


def equiv_status_path(root: Path | None = None) -> Path:
    env = (os.environ.get("GATE_EQUIV_STATUS") or "").strip()
    if env:
        return Path(env)
    if root is not None:
        return root / "scripts" / "gate" / "out" / EQUIV_STATUS_NAME
    return OUT_DIR / EQUIV_STATUS_NAME


def load_equiv_status(
    root: Path | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if data is not None:
        return data
    path = equiv_status_path(root)
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return obj if isinstance(obj, dict) else {}


def write_equiv_status(status: dict[str, Any], root: Path | None = None) -> Path:
    path = equiv_status_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _lookup_equiv(status: dict[str, Any], module: str) -> dict[str, Any] | None:
    rec = status.get(module)
    if isinstance(rec, dict):
        return rec
    return None


def _inherit_reason(rec: dict[str, Any] | None, required_boxes: list[str]) -> str | None:
    if rec is None:
        return "equiv result missing (not a real PASS in this CI run)"
    state = str(rec.get("status") or "").upper()
    if state in {"SKIP", "PRIVATE_SKIP"}:
        return f"equiv is {state}, not a real PASS"
    if state != "PASS":
        return f"equiv is {state or 'unknown'}, not PASS"
    boxed = {str(x) for x in (rec.get("blackboxes") or [])}
    missing = [name for name in required_boxes if name not in boxed]
    if missing:
        return (
            "missing EQUIV_BLACKBOX "
            + ",".join(missing)
            + " for inherited PRODUCT prove"
        )
    return None


def required_inherit_blackboxes(sby: Path, root: Path) -> list[str]:
    try:
        from formal_parent_free import (
            contract_output_ports,
            default_task_source_paths,
            instantiated_leaves,
        )
    except ImportError:
        return []
    leaves = set(contract_output_ports(root))
    if not leaves:
        return []
    inst: set[str] = set()
    for path in default_task_source_paths(sby, root):
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        inst |= instantiated_leaves(src, leaves)
    return sorted(inst)


def check_formal_inherit(
    root: Path,
    equiv_status: dict[str, Any] | None = None,
) -> list[Finding]:
    status = load_equiv_status(root, equiv_status)
    findings: list[Finding] = []
    for sby in discover_sby_files(root):
        try:
            text = sby.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not sby_inherits_hooks_prove(text):
            continue
        rec = _lookup_equiv(status, sby.stem)
        boxes = required_inherit_blackboxes(sby, root)
        reason = _inherit_reason(rec, boxes)
        file_rel = _sby_rel(sby, root)
        if reason is None:
            print(f"PRODUCT {sby.stem}: {INHERIT_STATUS}")
            continue
        findings.append(
            Finding(
                check="formal",
                module=sby.stem,
                file=file_rel,
                rule="FORMAL_INHERIT_NO_EQUIV",
                message=(
                    f"PRODUCT prove cannot inherit HOOKS prove: {reason}; "
                    "fall back to GATE-FORMAL-DEPTH (2)"
                ),
                bucket="report",
                severity="warning",
            )
        )
    return findings


def check_formal_bmc(root: Path) -> list[Finding]:
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
        findings.append(
            Finding(
                check="formal",
                module=sby.stem,
                file=_sby_rel(sby, root),
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


def check_formal_depth(
    root: Path,
    equiv_status: dict[str, Any] | None = None,
) -> list[Finding]:
    return check_formal_bmc(root) + check_formal_inherit(root, equiv_status)


def main() -> int:
    findings = check_formal_depth(REPO_ROOT)
    inherit = sum(1 for f in findings if f.rule == "FORMAL_INHERIT_NO_EQUIV")
    shallow = sum(1 for f in findings if f.rule == "FORMAL_BMC_SHALLOW")
    print(
        f"formal depth: {len(discover_sby_files(REPO_ROOT))} .sby, "
        f"{shallow} FORMAL_BMC_SHALLOW, {inherit} FORMAL_INHERIT_NO_EQUIV "
        "(report-only)"
    )
    return emit_report("formal_depth", findings)


if __name__ == "__main__":
    raise SystemExit(main())
