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
    collect_placeholder_policy_findings,
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
    proc = run_cmd(["bash", str(SETUP_SCRIPT)], timeout=600)
    print(proc.stdout or "")
    if SETUP_LOG.is_file():
        return SETUP_LOG.read_text(encoding="utf-8", errors="replace")
    return proc.stdout or ""


def _pycc_bin() -> str | None:
    found = shutil_which("pycc")
    if found:
        return found
    prefix = REPO_ROOT / ".pycircuit_out" / "toolchain" / "install" / "bin" / "pycc"
    if prefix.is_file():
        os.environ["PATH"] = f"{prefix.parent}:{os.environ.get('PATH', '')}"
        os.environ.setdefault("PYC_TOOLCHAIN_ROOT", str(prefix.parent.parent))
        return str(prefix)
    return None


def _venv_python() -> str:
    venv = REPO_ROOT / ".pycircuit-venv" / "bin" / "python"
    return str(venv) if venv.is_file() else sys.executable


def toolchain_ready() -> bool:
    if _pycc_bin() is None:
        return False
    proc = run_cmd([_venv_python(), "-c", "import pycircuit"], timeout=30)
    return proc.returncode == 0


def try_pycc_emit(leaf: dict, ready: bool) -> list[Finding]:
    """Regenerate PRODUCT/HOOKS with pycc and byte-compare.

    Blocking when the toolchain installed; report-only if setup failed.
    """
    bucket = "new" if ready else "report"
    suffix = "" if ready else " (report-only; toolchain not installed)"
    src = REPO_ROOT / leaf["source"]
    if not src.is_file() or is_handwritten_path(src):
        return []
    if leaf.get("placeholder"):
        print(f"pycc skip {leaf['module']}: _placeholder (lint/TB only)")
        return []
    pycc = _pycc_bin()
    if not pycc:
        return [
            Finding(
                check="provenance",
                module=leaf["module"],
                file=leaf["source"],
                rule="PYCC_UNAVAILABLE",
                message="pycc not on PATH after setup_pycircuit.sh" + suffix,
                bucket=bucket,
            )
        ]
    work = OUT_DIR / "pycc" / leaf["layer"] / leaf["module"]
    work.mkdir(parents=True, exist_ok=True)
    mlir = work / "out.mlir"
    py = _venv_python()
    emit_argv = [
        py,
        "-m",
        "pycircuit.cli",
        "emit",
        str(src),
        "-o",
        str(mlir),
        "--project-root",
        str(src.parent),
    ]
    for key, val in (leaf.get("params") or {}).items():
        emit_argv.extend(["--param", f"{key}={val}"])
    print(f"--- pycc emit {leaf['source']} variant={leaf['module']} ---")
    proc = run_cmd(emit_argv, timeout=120)
    print("\n".join((proc.stdout or "").strip().splitlines()[-20:] or [""]))
    if proc.returncode != 0:
        # Fall back to a direct pycc invocation if the CLI entry is missing.
        proc = run_cmd([pycc, str(src), "-o", str(work / "direct.v")], timeout=120)
        print("\n".join((proc.stdout or "").strip().splitlines()[-20:] or [""]))
        if proc.returncode != 0:
            return [
                Finding(
                    check="provenance",
                    module=leaf["module"],
                    file=leaf["source"],
                    rule="PYCC_EMIT_FAIL",
                    message=f"pycc/cli emit exited {proc.returncode}{suffix}",
                    bucket=bucket,
                )
            ]
    else:
        vlog = work / f"{leaf['module']}.v"
        proc = run_cmd(
            [pycc, str(mlir), "--emit=verilog", "--include-primitives=0", "-o", str(vlog)],
            timeout=120,
        )
        print("\n".join((proc.stdout or "").strip().splitlines()[-20:] or [""]))
        if proc.returncode != 0:
            return [
                Finding(
                    check="provenance",
                    module=leaf["module"],
                    file=leaf["source"],
                    rule="PYCC_EMIT_FAIL",
                    message=f"pycc mlir→verilog exited {proc.returncode}{suffix}",
                    bucket=bucket,
                )
            ]
    findings: list[Finding] = []
    for kind, dest in (("product", leaf["product"]), ("hooks", leaf["hooks"])):
        committed = REPO_ROOT / dest
        generated = None
        candidates = list(work.rglob("*.v"))
        if kind == "hooks":
            hooks_cands = [p for p in candidates if "hooks" in {x.lower() for x in p.parts}]
            generated = hooks_cands[0] if hooks_cands else None
        else:
            named = [p for p in candidates if p.name == f"{leaf['module']}.v"]
            generated = named[0] if named else (candidates[0] if candidates else None)
        if generated is None or not committed.is_file():
            findings.append(
                Finding(
                    check="provenance",
                    module=leaf["module"],
                    file=dest,
                    rule="PYCC_EMIT_MISSING",
                    message=f"pycc did not produce a {kind} netlist to compare{suffix}",
                    bucket=bucket,
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
                    message=f"pycc {kind} netlist differs from committed {dest}{suffix}",
                    bucket=bucket,
                )
            )
    return findings


def main() -> int:
    print_tool_versions(["python", "pycc", "llvm"])
    print(
        "pycircuit pin: lukebest/pyCircuit pyc4.0 "
        "(commit and package version in TOOLCHAIN.lock)"
    )
    leaves = discover_pycircuit_leaves()
    print(f"discovered pycircuit variants: {len(leaves)}")
    seen_src: set[str] = set()
    for leaf in leaves:
        tag = "migrate" if is_migrate_path(REPO_ROOT / leaf["source"]) else "new"
        ph = " placeholder" if leaf.get("placeholder") else ""
        print(f"  [{tag}{ph}] {leaf['source']} -> {leaf['module']}")
        seen_src.add(leaf["source"])

    findings: list[Finding] = []
    findings.extend(collect_placeholder_policy_findings("provenance"))
    for source in sorted(seen_src):
        if Path(source).name in SKIP_PY:
            continue
        leaf = next(L for L in leaves if L["source"] == source)
        findings.extend(static_check(leaf))

    print("=== pycc setup (blocking emit compare when SETUP_OK=1) ===")
    log = run_setup()
    ready = "SETUP_OK=1" in log or toolchain_ready()
    if "BLOCKER" in log and not ready:
        print("setup blockers recorded in scripts/gate/out/pycircuit_setup.log")
    if not leaves:
        print("no pycircuit/<layer>/*.py leaves on this branch")
    elif not ready:
        findings.append(
            Finding(
                check="provenance",
                module="*",
                file="scripts/gate/setup_pycircuit.sh",
                rule="PYCC_UNAVAILABLE",
                message="toolchain setup did not finish; pycc emit compare is report-only",
                bucket="report",
            )
        )
    else:
        for leaf in leaves:
            if Path(leaf["source"]).name in SKIP_PY:
                continue
            findings.extend(try_pycc_emit(leaf, ready=True))
    return emit_report("provenance", findings)


if __name__ == "__main__":
    raise SystemExit(main())
