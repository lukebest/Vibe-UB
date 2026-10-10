#!/usr/bin/env python3
"""pycircuit-provenance: static API check (blocking) + pycc emit (report-only).

Static (blocks new leaves; migrate list is 迁移待办):
  - every pycircuit/<layer>/*.py leaf imports pyCircuit
  - string literals must not splice Verilog (`module `, `endmodule`, `always @`)
  - handwritten whitelist is not subject to this check

pycc emit (report-only until the toolchain installs cleanly):
  - regenerate PRODUCT + HOOKS via pycc and byte-compare committed .v
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
    GATE_DIR,
    OUT_DIR,
    REPO_ROOT,
    Finding,
    discover_pycircuit_leaves,
    emit_report,
    is_handwritten_path,
    is_migrate_path,
    print_tool_versions,
    rel,
    run_cmd,
    shutil_which,
)

VERILOG_NEEDLES = ("module ", "endmodule", "always @", "always@")
SKIP_PY = {"__init__.py", "emit.py", "selfcheck.py"}
SETUP_SCRIPT = GATE_DIR / "setup_pycircuit.sh"
SETUP_LOG = OUT_DIR / "pycircuit_setup.log"


def _imports_pycircuit(tree: ast.AST) -> bool:
    """ast.Import / ast.ImportFrom whose module is pycircuit or pycircuit.*."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pycircuit" or alias.name.startswith("pycircuit."):
                    return True
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "pycircuit" or node.module.startswith("pycircuit."):
                return True
    return False


def _docstring_constants(tree: ast.AST) -> set[ast.AST]:
    """First statement of module / class / function if it is a string Expr."""
    skip: set[ast.AST] = set()

    def mark(node: ast.AST) -> None:
        body = getattr(node, "body", None)
        if not body:
            return
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            skip.add(first.value)

    if isinstance(tree, ast.Module):
        mark(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            mark(node)
    return skip


def _code_strings(tree: ast.AST) -> list[str]:
    """String constants and f-string parts in code; skip comments + docstrings.

    Comments never reach the AST. Docstrings are the first Expr(Constant[str])
    of a module, class, or function and are excluded here.
    """
    docs = _docstring_constants(tree)
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node in docs:
                continue
            out.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    out.append(part.value)
    return out


def static_check(leaf: dict[str, str]) -> list[Finding]:
    path = REPO_ROOT / leaf["source"]
    if not path.is_file():
        return []
    if is_handwritten_path(path):
        return []
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [
            Finding(
                check="provenance",
                module=leaf["module"],
                file=leaf["source"],
                rule="PY_SYNTAX",
                message=f"cannot parse leaf: {exc}",
            )
        ]
    if not _imports_pycircuit(tree):
        findings.append(
            Finding(
                check="provenance",
                module=leaf["module"],
                file=leaf["source"],
                rule="NO_PYCIRCUIT_IMPORT",
                message=(
                    "leaf does not import pyCircuit "
                    "(lukebest/pyCircuit pyc4.0, pin 43cc5918)"
                ),
            )
        )
    hits = sorted(
        {
            needle
            for blob in _code_strings(tree)
            for needle in VERILOG_NEEDLES
            if needle in blob
        }
    )
    if hits:
        findings.append(
            Finding(
                check="provenance",
                module=leaf["module"],
                file=leaf["source"],
                rule="VERILOG_SPLICE",
                message=(
                    "string literals splice Verilog text "
                    f"{hits}; use the pyCircuit modeling API"
                ),
            )
        )
    return findings


def run_setup() -> str:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not SETUP_SCRIPT.is_file():
        return "setup script missing"
    proc = run_cmd(["bash", str(SETUP_SCRIPT)], timeout=300)
    print(proc.stdout or "")
    if SETUP_LOG.is_file():
        return SETUP_LOG.read_text(encoding="utf-8", errors="replace")
    return proc.stdout or ""


def try_pycc_emit(leaf: dict[str, str]) -> list[Finding]:
    """Report-only: regenerate PRODUCT/HOOKS with pycc and byte-compare."""
    findings: list[Finding] = []
    pycc = shutil_which("pycc")
    if not pycc:
        prefix = REPO_ROOT / ".pycircuit_out" / "toolchain" / "install" / "bin" / "pycc"
        if prefix.is_file():
            pycc = str(prefix)
            os.environ["PATH"] = f"{prefix.parent}:{os.environ.get('PATH', '')}"
            os.environ.setdefault(
                "PYC_TOOLCHAIN_ROOT", str(prefix.parent.parent)
            )
    src = REPO_ROOT / leaf["source"]
    if not src.is_file() or is_handwritten_path(src):
        return findings
    if not pycc:
        return [
            Finding(
                check="provenance",
                module=leaf["module"],
                file=leaf["source"],
                rule="PYCC_UNAVAILABLE",
                message="pycc not on PATH after setup_pycircuit.sh (report-only)",
                bucket="report",
            )
        ]
    work = OUT_DIR / "pycc" / leaf["layer"] / leaf["module"]
    work.mkdir(parents=True, exist_ok=True)
    argv = [
        pycc,
        str(src),
        "--out-dir",
        str(work),
        "--target",
        "verilog",
    ]
    print(f"--- pycc emit {leaf['source']} ---")
    proc = run_cmd(argv, timeout=120)
    print("\n".join((proc.stdout or "").strip().splitlines()[-30:] or [""]))
    if proc.returncode != 0:
        return [
            Finding(
                check="provenance",
                module=leaf["module"],
                file=leaf["source"],
                rule="PYCC_EMIT_FAIL",
                message=f"pycc exited {proc.returncode} (report-only)",
                bucket="report",
            )
        ]
    for kind, dest in (("product", leaf["product"]), ("hooks", leaf["hooks"])):
        committed = REPO_ROOT / dest
        generated = None
        candidates = list(work.rglob(f"{leaf['module']}.v"))
        if kind == "hooks":
            hooks_cands = [p for p in candidates if "hooks" in {x.lower() for x in p.parts}]
            generated = hooks_cands[0] if hooks_cands else (candidates[0] if candidates else None)
        else:
            product_cands = [
                p for p in candidates if "hooks" not in {x.lower() for x in p.parts}
            ]
            generated = product_cands[0] if product_cands else (candidates[0] if candidates else None)
        if generated is None or not committed.is_file():
            findings.append(
                Finding(
                    check="provenance",
                    module=leaf["module"],
                    file=dest,
                    rule="PYCC_EMIT_MISSING",
                    message=f"pycc did not produce a {kind} netlist to compare (report-only)",
                    bucket="report",
                )
            )
            continue
        if generated.read_bytes() != committed.read_bytes():
            findings.append(
                Finding(
                    check="provenance",
                    module=leaf["module"],
                    file=dest,
                    rule="PYCC_EMIT_DIFF",
                    message=f"pycc {kind} netlist differs from committed {dest} (report-only)",
                    bucket="report",
                )
            )
    return findings


def main() -> int:
    print_tool_versions(["python", "pycc"])
    print(
        "pycircuit pin: lukebest/pyCircuit pyc4.0 "
        "43cc5918e3d09ecc0c814cabef6c1384cb9980ae"
    )
    leaves = discover_pycircuit_leaves()
    print(f"discovered pycircuit leaves: {len(leaves)}")
    for leaf in leaves:
        tag = "migrate" if is_migrate_path(REPO_ROOT / leaf["source"]) else "new"
        print(f"  [{tag}] {leaf['source']}")

    findings: list[Finding] = []
    for leaf in leaves:
        if Path(leaf["source"]).name in SKIP_PY:
            continue
        findings.extend(static_check(leaf))

    print("=== pycc setup (report-only emit path) ===")
    log = run_setup()
    if "BLOCKER" in log:
        print("setup blockers recorded in scripts/gate/out/pycircuit_setup.log")
    for leaf in leaves:
        if Path(leaf["source"]).name in SKIP_PY:
            continue
        findings.extend(try_pycc_emit(leaf))
    if not leaves:
        print("no pycircuit/<layer>/*.py leaves on this branch")
    return emit_report("provenance", findings)


if __name__ == "__main__":
    raise SystemExit(main())
