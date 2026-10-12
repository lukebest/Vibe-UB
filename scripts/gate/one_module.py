"""GATE-ONE-MODULE-PER-FILE: one `module` per file under rtl/.

`rtl/pyc_lib/` is excluded (pycc helpers). Extra module that is a
contract private leaf → PRIVATE_IN_PARENT (blocks after #47). Generic
MULTI_MODULE stays report-only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import Finding, REPO_ROOT, emit_report, rel, run_cmd, strip_verilog_comments
from private_leaves import discover_contract_files, parse_contract_file

MODULE_RE = re.compile(r"(?m)^\s*module\s+([A-Za-z_][A-Za-z0-9_$]*)")
RTL_SUFFIX = {".v", ".sv"}


def private_leaf_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in discover_contract_files(root):
        data, _errs = parse_contract_file(path, root)
        if data and data.get("leaf"):
            names.add(str(data["leaf"]).strip())
    return names


def private_in_parent_required(root: Path) -> bool:
    proc = run_cmd(
        ["git", "show", "origin/main:docs/rules/verif_gate.md"],
        cwd=root,
    )
    if proc.returncode != 0:
        return False
    return "PRIVATE_IN_PARENT" in (proc.stdout or "")


def iter_rtl_files(root: Path) -> list[Path]:
    rtl = root / "rtl"
    if not rtl.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(rtl.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in RTL_SUFFIX:
            continue
        if "pyc_lib" in path.relative_to(rtl).parts:
            continue
        out.append(path)
    return out


def modules_defined(text: str) -> list[str]:
    return MODULE_RE.findall(strip_verilog_comments(text))


def check_one_module(root: Path) -> list[Finding]:
    leaves = private_leaf_names(root)
    parent_bucket = "new" if private_in_parent_required(root) else "report"
    findings: list[Finding] = []
    for path in iter_rtl_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        names = modules_defined(text)
        if len(names) <= 1:
            continue
        extras = names[1:]
        file_rel = rel(path)
        private = [n for n in extras if n in leaves]
        if private:
            findings.append(
                Finding(
                    check="lint",
                    module=names[0],
                    file=file_rel,
                    rule="PRIVATE_IN_PARENT",
                    message=(
                        "private leaf "
                        + ",".join(private)
                        + f" defined inside {file_rel} (CODING_STYLE: one module per file)"
                    ),
                    bucket=parent_bucket,
                    severity="error" if parent_bucket == "new" else "warning",
                )
            )
        generic = [n for n in extras if n not in leaves]
        if generic or not private:
            extra_list = extras if not private else generic
            if extra_list:
                findings.append(
                    Finding(
                        check="lint",
                        module=names[0],
                        file=file_rel,
                        rule="MULTI_MODULE",
                        message=(
                            f"{file_rel} defines {len(names)} modules "
                            f"{names} (CODING_STYLE: one module per file)"
                        ),
                        bucket="report",
                        severity="warning",
                    )
                )
    return findings


def main() -> int:
    findings = check_one_module(REPO_ROOT)
    print(
        f"one-module: {len(iter_rtl_files(REPO_ROOT))} rtl files, "
        f"{len(findings)} findings"
    )
    return emit_report("one_module", findings)


if __name__ == "__main__":
    raise SystemExit(main())
