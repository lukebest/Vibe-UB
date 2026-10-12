"""S-01(b) private-leaf registry, contracts, stubs, attests, role dirs.

Public gate reads attests at reports/private/<layer>/<leaf>.yml.
Private-repo CI writes attest/<layer>/<leaf>.yml and copies it here.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contract_hash import (  # noqa: E402
    FENCE_RE,
    FRONT_MATTER_RE,
    contract_sha256,
    extract_contract_yaml,
)
from gatelib import (  # noqa: E402
    Finding,
    LOCK_SCAN_SKIP_DIRS,
    REPO_ROOT,
    load_yaml,
    run_cmd,
)

PRIVATE_LIST = Path(__file__).resolve().parent / "private_leaves.yml"
AP_RE = re.compile(r"`(AP_[A-Z0-9_]+)`")
ASSERT_README_RE = re.compile(
    r"^\|\s*`?assertions`?\s*\|[^\n]*必填",
    re.M,
)
HASH_DEF_RE = re.compile(
    r"^[ \t]*(?:async[ \t]+)?def[ \t]+(contract_sha256|contract_hash)[ \t]*\(",
    re.M,
)
HASH_SINGLE_MAX_READ = 2_000_000
LEAF_TICK_RE = re.compile(r"`(ub_[a-z0-9_]+)`")
UARCH_H2_RE = re.compile(r"^##[ \t]+(\d+)\b", re.M)
PLAIN_LEAF_RE = re.compile(r"\Aub_[a-z0-9_]+\Z")
HASH_HEADER_RE = re.compile(
    r"contract_sha256:\s*([0-9a-fA-F]{64}|HANDWRITTEN)\b"
)
GENERATED_BY = "scripts/gate/gen_private_stub.py"
ROLE_DIRS = ("design", "model", "verif", "impl")
ATTEST_DIR = "reports/private"
CRIT_PATH_OK = {"public", "私有叶子内部"}
STATUS_OK = {"PASS", "FAIL"}

REQUIRED_TOP = (
    "leaf",
    "parent",
    "clock",
    "latency",
    "ports",
    "params",
    "ill_cause_width",
)
CLOCK_KEYS = ("name", "period_ns", "reset", "reset_type")
PORT_KEYS = ("name", "dir", "width", "desc")
ATTEST_TOP = (
    "leaf",
    "contract_sha256",
    "netlist_sha256",
    "toolchain_sha256",
    "clock",
    "cells",
    "area_um2",
    "regs",
    "logic_depth",
    "depth_incl_buf",
    "wns_ns",
    "crit_path",
    "status",
)


def discover_contract_files(root: Path) -> list[Path]:
    """docs/arch/<layer>/contracts/*.md including pcs; skip README."""
    files: list[Path] = []
    arch = root / "docs" / "arch"
    if not arch.is_dir():
        return files
    for layer_dir in sorted(p for p in arch.iterdir() if p.is_dir()):
        contracts = layer_dir / "contracts"
        if not contracts.is_dir():
            continue
        for path in sorted(contracts.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            files.append(path)
    return files


def _private_yml(root: Path | None) -> Path:
    if root is not None:
        return root / "scripts" / "gate" / "private_leaves.yml"
    return PRIVATE_LIST


def load_private_config(root: Path | None = None) -> dict[str, Any]:
    path = _private_yml(root)
    if not path.is_file():
        return {}
    data = load_yaml(path)
    return data if isinstance(data, dict) else {}


def assertions_required(root: Path) -> bool:
    """Blocking once README §8 marks assertions 必填, or yml override.

    `private_leaves.yml` `assertions_required: true|false` wins.
    Otherwise any `docs/arch/*/contracts/README.md` row
    `| assertions | … 必填` (the #49 mark) flips the gate on.
    """
    flag = load_private_config(root).get("assertions_required")
    if flag is True or flag is False:
        return bool(flag)
    arch = root / "docs" / "arch"
    if not arch.is_dir():
        return False
    for readme in sorted(arch.glob("*/contracts/README.md")):
        try:
            text = readme.read_text(encoding="utf-8")
        except OSError:
            continue
        if ASSERT_README_RE.search(text):
            return True
    return False


def hash_single_required(root: Path) -> bool:
    """Blocking once #47 is on main, or yml override.

    Same switch style as GATE-CONTRACT-004: `hash_single_required`
    in private_leaves.yml wins; otherwise origin/main's verif_gate.md
    carrying GATE-CONTRACT-HASH-SINGLE means the rule has landed.
    """
    flag = load_private_config(root).get("hash_single_required")
    if flag is True or flag is False:
        return bool(flag)
    proc = run_cmd(
        ["git", "show", "origin/main:docs/rules/verif_gate.md"],
        cwd=root,
    )
    if proc.returncode != 0:
        return False
    return "GATE-CONTRACT-HASH-SINGLE" in (proc.stdout or "")


def contract_prose(text: str) -> str:
    """Markdown after the leading YAML segment (front matter or ```yaml)."""
    m = FRONT_MATTER_RE.match(text)
    if m:
        return text[m.end() :]
    m = FENCE_RE.match(text)
    if m:
        return text[m.end() :]
    return text


def load_private_names(root: Path | None = None) -> set[str]:
    data = load_private_config(root)
    names: set[str] = set()
    for item in data.get("leaves") or []:
        if isinstance(item, str) and item.strip():
            names.add(item.strip())
        elif isinstance(item, dict):
            name = str(item.get("leaf") or item.get("name") or "").strip()
            if name:
                names.add(name)
    return names


def is_private_leaf(name: str, root: Path | None = None) -> bool:
    names = load_private_names(root)
    return any(name == n or name.startswith(n + "_") for n in names)


def private_skip_finding(check: str, module: str, file: str) -> Finding:
    return Finding(
        check=check,
        module=module,
        file=file,
        rule="PRIVATE_SKIP",
        message="S-01(b) private leaf: public tree has contract+stub only; skip this job",
        bucket="report",
    )


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def layer_of_contract(path: Path, root: Path) -> str:
    try:
        parts = path.resolve().relative_to(root.resolve()).parts
    except ValueError:
        parts = path.parts
    if len(parts) >= 5 and parts[0] == "docs" and parts[1] == "arch":
        return parts[2]
    return "unknown"


def _uarch_section(text: str, number: int) -> str:
    """Body of `## N` up to the next `##` heading (exclusive)."""
    starts = [
        (m.start(), int(m.group(1))) for m in UARCH_H2_RE.finditer(text)
    ]
    for i, (pos, num) in enumerate(starts):
        if num != number:
            continue
        line_end = text.find("\n", pos)
        body_at = len(text) if line_end < 0 else line_end + 1
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        return text[body_at:end]
    return ""


def _md_table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in section.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
            continue
        rows.append(cells)
    return rows


def _leaf_name_column(header: list[str]) -> int:
    """Prefer the '本草案叶子' / '叶子' column; fall back to the first cell."""
    for i, cell in enumerate(header):
        title = cell.replace("`", "").strip()
        if "叶子" in title and "职责" not in title:
            return i
    return 0


def _row_leaf_name(cell: str) -> str | None:
    """Own-row identity of one §3 leaf-name cell.

    Strip backticks/whitespace. A cell that is exactly one `ub_*` name
    is that row. A combined `A + B + C` cell is one row owned by A
    (the first name) until design splits B/C into their own rows.
    Description text is not passed in.
    """
    if not cell or cell in {"—", "-", "–"}:
        return None
    ticks = LEAF_TICK_RE.findall(cell)
    if ticks:
        return ticks[0]
    plain = cell.replace("`", "").strip()
    if PLAIN_LEAF_RE.fullmatch(plain):
        return plain
    return None


def load_uarch_leaves(root: Path, layer: str) -> set[str]:
    """Leaf names that have their own row in UARCH.md §3 (leaf-name column)."""
    path = root / "docs" / "arch" / layer / "UARCH.md"
    if not path.is_file():
        return set()
    section = _uarch_section(path.read_text(encoding="utf-8"), 3)
    if not section:
        return set()
    rows = _md_table_rows(section)
    if not rows:
        return set()
    idx = _leaf_name_column(rows[0])
    names: set[str] = set()
    for row in rows[1:]:
        if idx >= len(row):
            continue
        name = _row_leaf_name(row[idx])
        if name:
            names.add(name)
    return names


def load_inventory_leaves(root: Path) -> set[str]:
    names: set[str] = set()
    for cand in (
        root / "docs" / "arch" / "MODULE_INVENTORY.yml",
        root / "docs" / "arch" / "MODULE_INVENTORY.yaml",
        root / "docs" / "MODULE_INVENTORY.yml",
    ):
        if not cand.is_file():
            continue
        names.update(_walk_names(load_yaml(cand)))
    return names


def _walk_names(node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        for key, val in node.items():
            if key in {"leaf", "module", "name", "id"} and isinstance(val, str):
                if val.startswith("ub_"):
                    found.add(val)
            found.update(_walk_names(val))
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, str) and item.startswith("ub_"):
                found.add(item)
            else:
                found.update(_walk_names(item))
    return found


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _is_combo(latency: dict[str, Any]) -> bool:
    kind = str(latency.get("kind") or latency.get("type") or "").strip().lower()
    return kind == "combinational" or latency.get("cycles") == 0


def parse_contract_file(
    path: Path, root: Path
) -> tuple[dict[str, Any] | None, list[Finding]]:
    findings: list[Finding] = []
    file_rel = _rel(path, root)
    leaf_from_name = path.stem
    text = path.read_text(encoding="utf-8")
    yaml_body = extract_contract_yaml(text)
    if yaml_body is None:
        findings.append(
            Finding(
                check="contract",
                module=leaf_from_name,
                file=file_rel,
                rule="CONTRACT_YAML",
                message="contract must start with --- YAML --- (or a ```yaml fence)",
            )
        )
        return None, findings
    try:
        import yaml  # type: ignore
    except ImportError:
        findings.append(
            Finding(
                check="contract",
                module=leaf_from_name,
                file=file_rel,
                rule="CONTRACT_YAML",
                message="PyYAML is required to parse contract YAML",
            )
        )
        return None, findings
    data = yaml.safe_load(yaml_body)
    if not isinstance(data, dict):
        findings.append(
            Finding(
                check="contract",
                module=leaf_from_name,
                file=file_rel,
                rule="CONTRACT_YAML",
                message="YAML segment must parse to a mapping",
            )
        )
        return None, findings
    try:
        digest = contract_sha256(path)
    except ValueError as exc:
        findings.append(
            Finding(
                check="contract",
                module=leaf_from_name,
                file=file_rel,
                rule="CONTRACT_YAML",
                message=str(exc),
            )
        )
        return None, findings
    data["_yaml_hash"] = digest
    data["_body"] = contract_prose(text)
    data["_path"] = file_rel
    data["_layer"] = layer_of_contract(path, root)
    return data, findings


def _assert_bucket(root: Path) -> str:
    return "new" if assertions_required(root) else "report"


def _assertion_findings(
    data: dict[str, Any], root: Path, file_rel: str, module: str
) -> list[Finding]:
    """assertions: required non-empty list; body `AP_*` must match 1-1.

    Report-only until README §8 marks the field 必填 (or yml override).
    """
    findings: list[Finding] = []
    bucket = _assert_bucket(root)
    raw = data.get("assertions") if "assertions" in data else None
    if raw is None or raw == []:
        findings.append(
            Finding(
                check="contract",
                module=module,
                file=file_rel,
                rule="CONTRACT_FIELD_MISSING",
                message="assertions is required and must be a non-empty list",
                bucket=bucket,
                severity="error" if bucket == "new" else "warning",
            )
        )
    elif not isinstance(raw, list) or not all(isinstance(x, str) for x in raw):
        findings.append(
            Finding(
                check="contract",
                module=module,
                file=file_rel,
                rule="CONTRACT_FIELD",
                message="assertions must be a list of strings",
                bucket=bucket,
                severity="error" if bucket == "new" else "warning",
            )
        )
        raw = []
    listed = {str(x).strip() for x in (raw or []) if isinstance(x, str) and str(x).strip()}
    body = set(AP_RE.findall(str(data.get("_body") or "")))
    for name in sorted(body - listed):
        findings.append(
            Finding(
                check="contract",
                module=module,
                file=file_rel,
                rule="CONTRACT_ASSERT_UNLISTED",
                message=f"body assertion {name} is not in YAML assertions",
                bucket=bucket,
                severity="error" if bucket == "new" else "warning",
            )
        )
    for name in sorted(listed - body):
        findings.append(
            Finding(
                check="contract",
                module=module,
                file=file_rel,
                rule="CONTRACT_ASSERT_UNUSED",
                message=f"YAML assertion {name} is not referenced in the body",
                bucket=bucket,
                severity="error" if bucket == "new" else "warning",
            )
        )
    return findings


def validate_contract(data: dict[str, Any], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    file_rel = str(data.get("_path") or "")
    leaf = data.get("leaf")
    module = str(leaf) if isinstance(leaf, str) else Path(file_rel).stem

    for key in REQUIRED_TOP:
        if key not in data:
            findings.append(
                Finding(
                    check="contract",
                    module=module,
                    file=file_rel,
                    rule="CONTRACT_FIELD",
                    message=f"missing required field {key!r} (contracts README §8)",
                )
            )
    if "leaf" in data and not isinstance(data["leaf"], str):
        findings.append(
            Finding(
                check="contract",
                module=module,
                file=file_rel,
                rule="CONTRACT_FIELD",
                message="leaf must be a string",
            )
        )
    elif isinstance(leaf, str) and Path(file_rel).stem != leaf:
        findings.append(
            Finding(
                check="contract",
                module=module,
                file=file_rel,
                rule="CONTRACT_FIELD",
                message=f"leaf {leaf!r} must match filename stem {Path(file_rel).stem!r}",
            )
        )
    if "parent" in data and not isinstance(data["parent"], str):
        findings.append(
            Finding(
                check="contract",
                module=module,
                file=file_rel,
                rule="CONTRACT_FIELD",
                message="parent must be a string",
            )
        )

    clock = data.get("clock")
    if "clock" in data:
        if not isinstance(clock, dict):
            findings.append(
                Finding(
                    check="contract",
                    module=module,
                    file=file_rel,
                    rule="CONTRACT_FIELD",
                    message="clock must be {name,period_ns,reset,reset_type}",
                )
            )
        else:
            for ck in CLOCK_KEYS:
                if ck not in clock:
                    findings.append(
                        Finding(
                            check="contract",
                            module=module,
                            file=file_rel,
                            rule="CONTRACT_FIELD",
                            message=f"clock missing {ck}",
                        )
                    )
            if "period_ns" in clock and _as_number(clock["period_ns"]) is None:
                findings.append(
                    Finding(
                        check="contract",
                        module=module,
                        file=file_rel,
                        rule="CONTRACT_FIELD",
                        message="clock.period_ns must be a number",
                    )
                )

    latency = data.get("latency")
    if "latency" in data:
        if not isinstance(latency, dict):
            findings.append(
                Finding(
                    check="contract",
                    module=module,
                    file=file_rel,
                    rule="CONTRACT_FIELD",
                    message="latency must be {kind,cycles,max_cycles}",
                )
            )
            latency = {}
        else:
            kind = latency.get("kind") or latency.get("type")
            if kind not in {"registered", "combinational"}:
                findings.append(
                    Finding(
                        check="contract",
                        module=module,
                        file=file_rel,
                        rule="CONTRACT_FIELD",
                        message="latency.kind must be registered or combinational",
                    )
                )
            if "cycles" in latency and not isinstance(latency["cycles"], int):
                findings.append(
                    Finding(
                        check="contract",
                        module=module,
                        file=file_rel,
                        rule="CONTRACT_FIELD",
                        message="latency.cycles must be an int",
                    )
                )

    combo = _is_combo(latency) if isinstance(latency, dict) else False
    has_budget = "comb_budget_ns" in data
    if combo and not has_budget:
        findings.append(
            Finding(
                check="contract",
                module=module,
                file=file_rel,
                rule="COMB_BUDGET_MISSING",
                message="combinational / 0-cycle leaf must set comb_budget_ns",
            )
        )
    if (not combo) and has_budget and isinstance(latency, dict):
        findings.append(
            Finding(
                check="contract",
                module=module,
                file=file_rel,
                rule="COMB_BUDGET_UNEXPECTED",
                message="registered leaf must not set comb_budget_ns",
            )
        )
    if has_budget and _as_number(data.get("comb_budget_ns")) is None:
        findings.append(
            Finding(
                check="contract",
                module=module,
                file=file_rel,
                rule="CONTRACT_FIELD",
                message="comb_budget_ns must be a number",
            )
        )

    ports = data.get("ports")
    if "ports" in data:
        if not isinstance(ports, list):
            findings.append(
                Finding(
                    check="contract",
                    module=module,
                    file=file_rel,
                    rule="CONTRACT_FIELD",
                    message="ports must be a list of {name,dir,width,desc}",
                )
            )
        else:
            for i, port in enumerate(ports):
                if not isinstance(port, dict):
                    findings.append(
                        Finding(
                            check="contract",
                            module=module,
                            file=file_rel,
                            rule="CONTRACT_FIELD",
                            message=f"ports[{i}] must be a mapping",
                        )
                    )
                    continue
                for pk in PORT_KEYS:
                    if pk not in port:
                        findings.append(
                            Finding(
                                check="contract",
                                module=module,
                                file=file_rel,
                                rule="CONTRACT_FIELD",
                                message=f"ports[{i}] missing {pk}",
                            )
                        )
                if port.get("dir") not in {None, "in", "out"}:
                    findings.append(
                        Finding(
                            check="contract",
                            module=module,
                            file=file_rel,
                            rule="CONTRACT_FIELD",
                            message=f"ports[{i}].dir must be in or out",
                        )
                    )

    if "params" in data and not isinstance(data["params"], list):
        findings.append(
            Finding(
                check="contract",
                module=module,
                file=file_rel,
                rule="CONTRACT_FIELD",
                message="params must be a list",
            )
        )
    if "ill_cause_width" in data and not isinstance(data["ill_cause_width"], int):
        findings.append(
            Finding(
                check="contract",
                module=module,
                file=file_rel,
                rule="CONTRACT_FIELD",
                message="ill_cause_width must be an int",
            )
        )
    findings.extend(_assertion_findings(data, root, file_rel, module))

    parent = data.get("parent")
    if isinstance(parent, str) and parent:
        layer = str(data.get("_layer") or "unknown")
        known = load_uarch_leaves(root, layer) | load_inventory_leaves(root)
        if parent not in known:
            findings.append(
                Finding(
                    check="contract",
                    module=module,
                    file=file_rel,
                    rule="PARENT_UNKNOWN",
                    message=(
                        f"parent {parent!r} has no own row in "
                        f"docs/arch/{layer}/UARCH.md §3 leaf-name column "
                        "(description / other columns / + extras do not count)"
                    ),
                )
            )

    return findings


def check_all_contracts(root: Path) -> tuple[list[Finding], list[dict[str, Any]]]:
    findings: list[Finding] = []
    parsed: list[dict[str, Any]] = []
    for path in discover_contract_files(root):
        data, local = parse_contract_file(path, root)
        findings.extend(local)
        if data is None:
            continue
        findings.extend(validate_contract(data, root))
        parsed.append(data)
    return findings, parsed


def layer_from_leaf(name: str) -> str:
    parts = name.split("_")
    if len(parts) >= 3 and parts[0] == "ub":
        return parts[1]
    return "unknown"


def stub_rtl_path(root: Path, layer: str, leaf: str) -> Path:
    return root / "rtl" / layer / "stub" / f"{leaf}.v"


def stub_py_path(root: Path, layer: str, leaf: str) -> Path:
    return root / "pycircuit" / layer / "stub" / f"{leaf}.py"


def read_contract_hash_header(text: str) -> str | None:
    m = HASH_HEADER_RE.search(text)
    return m.group(1) if m else None


def script_on_origin_main() -> bool:
    proc = run_cmd(
        ["git", "cat-file", "-e", "origin/main:scripts/gate/gen_private_stub.py"]
    )
    return proc.returncode == 0


def check_stubs(root: Path, contracts: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    registered = load_private_names(root)
    by_leaf = {str(c.get("leaf")): c for c in contracts if c.get("leaf")}
    enforce = script_on_origin_main()
    for name in sorted(registered):
        data = by_leaf.get(name)
        layer = str(data.get("_layer") if data else layer_from_leaf(name))
        stub = stub_rtl_path(root, layer, name)
        file_rel = (
            stub.relative_to(root).as_posix() if stub.is_file() else stub.as_posix()
        )
        if not stub.is_file():
            findings.append(
                Finding(
                    check="contract",
                    module=name,
                    file=file_rel,
                    rule="STUB_MISSING",
                    message=(
                        "registered private leaf has no "
                        f"rtl/{layer}/stub/{name}.v; run gen_private_stub.py"
                    ),
                )
            )
            continue
        text = stub.read_text(encoding="utf-8")
        got = read_contract_hash_header(text)
        if got is None:
            findings.append(
                Finding(
                    check="contract",
                    module=name,
                    file=file_rel,
                    rule="STUB_HASH_MISSING",
                    message="stub header missing contract_sha256: <hex>|HANDWRITTEN",
                )
            )
            continue
        if got == "HANDWRITTEN":
            findings.append(
                Finding(
                    check="contract",
                    module=name,
                    file=file_rel,
                    rule="STUB_HANDWRITTEN",
                    message=(
                        "handwritten stub (contract_sha256: HANDWRITTEN); "
                        "regenerate with gen_private_stub.py after the script is on main"
                    ),
                    bucket="new" if enforce else "report",
                )
            )
            continue
        if data is None:
            continue
        expect = str(data.get("_yaml_hash") or "")
        if got.lower() != expect:
            findings.append(
                Finding(
                    check="contract",
                    module=name,
                    file=file_rel,
                    rule="STUB_HASH_MISMATCH",
                    message=(
                        f"rtl stub contract_sha256 {got[:12]}… != "
                        f"current contract {expect[:12]}…; re-run gen_private_stub.py"
                    ),
                )
            )
    return findings


def attest_path(root: Path, layer: str, leaf: str) -> Path:
    return root / ATTEST_DIR / layer / f"{leaf}.yml"


def check_attests(root: Path, contracts: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    registered = load_private_names(root)
    by_leaf = {str(c.get("leaf")): c for c in contracts if c.get("leaf")}
    for name in sorted(registered):
        data = by_leaf.get(name)
        layer = str(data.get("_layer") if data else layer_from_leaf(name))
        path = attest_path(root, layer, name)
        file_rel = f"{ATTEST_DIR}/{layer}/{name}.yml"
        if not path.is_file():
            findings.append(
                Finding(
                    check="contract",
                    module=name,
                    file=file_rel,
                    rule="ATTEST_MISSING",
                    message=(
                        f"private leaf needs {file_rel} "
                        f"(copy of private-repo attest/{layer}/{name}.yml)"
                    ),
                )
            )
            continue
        attest = load_yaml(path)
        if not isinstance(attest, dict):
            findings.append(
                Finding(
                    check="contract",
                    module=name,
                    file=file_rel,
                    rule="ATTEST_FIELD",
                    message="attest YAML must be a mapping",
                )
            )
            continue
        for key in ATTEST_TOP:
            if key not in attest:
                findings.append(
                    Finding(
                        check="contract",
                        module=name,
                        file=file_rel,
                        rule="ATTEST_FIELD",
                        message=f"missing field {key!r}",
                    )
                )
        ahash = str(attest.get("contract_sha256") or "").strip().lower()
        expect = str((data or {}).get("_yaml_hash") or "")
        if data is not None and ahash != expect:
            findings.append(
                Finding(
                    check="contract",
                    module=name,
                    file=file_rel,
                    rule="ATTEST_HASH_MISMATCH",
                    message="attest contract_sha256 does not match the current contract",
                )
            )
        clock = attest.get("clock") if isinstance(attest.get("clock"), dict) else {}
        if data is not None and isinstance(data.get("clock"), dict):
            exp_name = data["clock"].get("name")
            exp_period = _as_number(data["clock"].get("period_ns"))
            got_name = clock.get("name")
            got_period = _as_number(clock.get("period_ns"))
            if got_name != exp_name or got_period is None or exp_period is None:
                findings.append(
                    Finding(
                        check="contract",
                        module=name,
                        file=file_rel,
                        rule="ATTEST_CLOCK_MISMATCH",
                        message=(
                            f"attest clock {got_name!r} period={clock.get('period_ns')!r} "
                            f"!= contract {exp_name!r} period={exp_period!r}"
                        ),
                    )
                )
            elif abs(got_period - exp_period) > 1e-6:
                findings.append(
                    Finding(
                        check="contract",
                        module=name,
                        file=file_rel,
                        rule="ATTEST_CLOCK_MISMATCH",
                        message=(
                            f"attest period_ns {got_period} != contract {exp_period}"
                        ),
                    )
                )
        status = str(attest.get("status") or "")
        if "status" in attest and status != "PASS":
            findings.append(
                Finding(
                    check="contract",
                    module=name,
                    file=file_rel,
                    rule="ATTEST_STATUS",
                    message=f"attest status must be PASS, got {status!r}",
                )
            )
        if status and status not in STATUS_OK:
            findings.append(
                Finding(
                    check="contract",
                    module=name,
                    file=file_rel,
                    rule="ATTEST_FIELD",
                    message="status must be PASS or FAIL",
                )
            )
        crit = attest.get("crit_path")
        if crit is not None and crit not in CRIT_PATH_OK:
            findings.append(
                Finding(
                    check="contract",
                    module=name,
                    file=file_rel,
                    rule="ATTEST_FIELD",
                    message="crit_path must be 'public' or '私有叶子内部'",
                )
            )
        wns = _as_number(attest.get("wns_ns")) if "wns_ns" in attest else None
        if "wns_ns" in attest and (wns is None or wns < 0):
            findings.append(
                Finding(
                    check="contract",
                    module=name,
                    file=file_rel,
                    rule="ATTEST_WNS",
                    message=f"wns_ns must be >= 0, got {attest.get('wns_ns')!r}",
                )
            )
    return findings


def changed_paths_vs_main(root: Path) -> list[str]:
    verify = run_cmd(["git", "rev-parse", "--verify", "origin/main"], cwd=root)
    if verify.returncode != 0:
        print("NOTE: origin/main missing; skip role-directory scan")
        return []
    diff = run_cmd(["git", "diff", "--name-only", "origin/main...HEAD"], cwd=root)
    if diff.returncode != 0:
        return []
    return [ln.strip() for ln in diff.stdout.splitlines() if ln.strip()]


def role_title_ok(title: str, role: str) -> bool:
    t = title.lower()
    r = role.lower()
    return f"[{r}]" in t or t.startswith(f"{r}:") or f"({r})" in t


def check_role_dirs(
    paths: list[str], title: str | None = None
) -> list[Finding]:
    roles = sorted(
        {p.replace("\\", "/").lstrip("/").split("/", 1)[0] for p in paths}
        & set(ROLE_DIRS)
    )
    findings: list[Finding] = []
    if len(roles) > 1:
        findings.append(
            Finding(
                check="contract",
                module="*",
                file=",".join(roles),
                rule="ROLE_CROSS",
                message=(
                    f"PR touches more than one role directory {roles}; "
                    f"stay in one of {list(ROLE_DIRS)} (public/ is shared)"
                ),
            )
        )
    if len(roles) == 1:
        role = roles[0]
        if title is None:
            title = os.environ.get("GATE_PR_TITLE") or ""
        if title and not role_title_ok(title, role):
            findings.append(
                Finding(
                    check="contract",
                    module="*",
                    file=role,
                    rule="ROLE_TITLE",
                    message=f"PR title must carry role tag [{role}]",
                )
            )
    return findings


def _under_scripts_gate(rel: Path) -> bool:
    return rel.parts[:2] == ("scripts", "gate")


def _iter_tree_files(root: Path) -> list[Path]:
    skip = set(LOCK_SCAN_SKIP_DIRS) | {"sim_build"}
    out: list[Path] = []
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            kids = list(d.iterdir())
        except OSError:
            continue
        for child in kids:
            if child.is_symlink():
                continue
            if child.is_dir():
                if child.name in skip:
                    continue
                stack.append(child)
            elif child.is_file():
                out.append(child)
    return out


def check_hash_single(root: Path) -> list[Finding]:
    """GATE-CONTRACT-HASH-SINGLE: one hash impl, scripts/gate/contract_hash.py."""
    findings: list[Finding] = []
    bucket = "new" if hash_single_required(root) else "report"
    for path in _iter_tree_files(root):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if _under_scripts_gate(rel):
            continue
        reasons: list[str] = []
        if path.name == "contract_hash.py":
            reasons.append("module named contract_hash.py")
        if path.suffix == ".py":
            try:
                if path.stat().st_size > HASH_SINGLE_MAX_READ:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            names = sorted(set(HASH_DEF_RE.findall(text)))
            if names:
                reasons.append("def " + "/".join(names))
        if not reasons:
            continue
        findings.append(
            Finding(
                check="contract",
                module="*",
                file=rel.as_posix(),
                rule="CONTRACT_HASH_DUP",
                message=(
                    "own contract-hash implementation ("
                    + "; ".join(reasons)
                    + "); import scripts/gate/contract_hash.py instead"
                ),
                bucket=bucket,
                severity="error" if bucket == "new" else "warning",
            )
        )
    findings.sort(key=lambda f: f.file)
    return findings


def collect_contract_findings(
    root: Path | None = None,
    *,
    paths: list[str] | None = None,
    title: str | None = None,
) -> list[Finding]:
    root = root or REPO_ROOT
    findings, contracts = check_all_contracts(root)
    findings.extend(check_stubs(root, contracts))
    findings.extend(check_attests(root, contracts))
    findings.extend(check_hash_single(root))
    if paths is None:
        paths = changed_paths_vs_main(root)
    findings.extend(check_role_dirs(paths, title=title))
    return findings


def list_runnable_sby(root: Path) -> list[Path]:
    """formal/<iface>/*.sby only (GATE-FOR-002). Skip registered private leaves."""
    formal = root / "formal"
    if not formal.is_dir():
        return []
    out: list[Path] = []
    for iface in sorted(p for p in formal.iterdir() if p.is_dir()):
        for path in sorted(iface.glob("*.sby")):
            if is_private_leaf(path.stem, root):
                print(
                    f"PRIVATE_SKIP: {path.relative_to(root).as_posix()}",
                    file=sys.stderr,
                )
                continue
            out.append(path)
    return out


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["--list-sby"]:
        for path in list_runnable_sby(REPO_ROOT):
            print(path)
        return 0
    from gatelib import emit_report

    return emit_report("contract", collect_contract_findings())


if __name__ == "__main__":
    raise SystemExit(main())
