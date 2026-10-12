#!/usr/bin/env python3
"""Auto-discover pytest + cocotb under tb/ and pytest under model/.

Discovery (see docs/rules/verif_gate.md):
  - pytest: tb/**/test_*.py and tb/**/*_test.py that do not import cocotb
  - pytest: model/ when that directory exists
  - cocotb: tb/Makefile and tb/*/Makefile targets selfcheck-both (preferred)
    or selfcheck; run with SIM=icarus
  - never run D10 *_tb.v benches
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
    OUT_DIR,
    REPO_ROOT,
    leaf_process_env,
    print_tool_versions,
    rel,
    run_cmd,
    shutil_which,
)

COCOTB_IMPORT_RE = re.compile(
    r"^\s*(?:import\s+cocotb\b|from\s+cocotb\b)",
    re.M,
)
SKIP_PARTS = {
    "__pycache__",
    ".pytest_cache",
    "sim_build",
    ".venv",
    "venv",
    "out",
}
MAKE_TARGET_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s*:", re.M)


def _skip(path: Path) -> bool:
    return any(p in SKIP_PARTS for p in path.parts)


def is_pytest_filename(name: str) -> bool:
    return name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py")


def file_imports_cocotb(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(COCOTB_IMPORT_RE.search(text))


def discover_pytest_files() -> list[Path]:
    files: list[Path] = []
    tb = REPO_ROOT / "tb"
    if not tb.is_dir():
        return files
    for path in sorted(tb.rglob("*.py")):
        if _skip(path) or not path.is_file():
            continue
        if not is_pytest_filename(path.name):
            continue
        if file_imports_cocotb(path):
            print(f"pytest skip (cocotb): {rel(path)}")
            continue
        files.append(path)
    return files


def makefile_targets(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return set(MAKE_TARGET_RE.findall(text))


def discover_cocotb_makefiles() -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    tb = REPO_ROOT / "tb"
    candidates: list[Path] = []
    if (tb / "Makefile").is_file():
        candidates.append(tb / "Makefile")
    if tb.is_dir():
        for child in sorted(tb.iterdir()):
            mk = child / "Makefile"
            if child.is_dir() and mk.is_file():
                candidates.append(mk)
    for mk in candidates:
        targets = makefile_targets(mk)
        if "selfcheck-both" in targets:
            found.append((mk.parent, "selfcheck-both"))
        elif "selfcheck" in targets:
            found.append((mk.parent, "selfcheck"))
    return found


def required_sim_tools(which: Callable[[str], str | None] | None = None) -> list[str]:
    """Icarus is D7 pass/fail; Verilator is the tb/cmn RTL-sim tool (TOOLCHAIN.lock)."""
    probe = which or shutil_which
    missing: list[str] = []
    if not probe("iverilog"):
        missing.append("iverilog")
    if not probe("verilator"):
        missing.append("verilator")
    return missing


def parse_junit_counts(xml_path: Path) -> dict[str, object]:
    """Return collected/passed/failed/skipped plus skipped nodeids."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
    tests = failures = skipped = errors = 0
    skip_names: list[str] = []
    fail_names: list[str] = []
    for suite in suites:
        tests += int(suite.get("tests") or 0)
        failures += int(suite.get("failures") or 0)
        skipped += int(suite.get("skipped") or 0)
        errors += int(suite.get("errors") or 0)
        for case in suite.findall("testcase"):
            node = f"{case.get('classname') or ''}::{case.get('name') or ''}"
            if case.find("skipped") is not None:
                skip_names.append(node)
            if case.find("failure") is not None or case.find("error") is not None:
                fail_names.append(node)
    passed = tests - failures - skipped - errors
    return {
        "collected": tests,
        "passed": passed,
        "failed": failures + errors,
        "skipped": skipped,
        "skip_names": skip_names,
        "fail_names": fail_names,
    }


def pytest_skip_is_fail(counts: dict[str, object]) -> bool:
    return int(counts.get("skipped") or 0) > 0 or int(counts.get("failed") or 0) > 0


def suite_label(path: Path) -> str:
    rels = rel(path).replace("\\", "/")
    if rels.startswith("model/"):
        return "model/tests"
    if rels.startswith("tb/models/"):
        return "tb/models"
    if rels.startswith("tb/cmn/"):
        return "tb/cmn"
    return "tb/other"


def run_or_fail(argv: list[str], cwd: Path | None = None) -> int:
    print(f"=== {' '.join(argv)} ===")
    proc = run_cmd(argv, cwd=cwd, env=leaf_process_env())
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.returncode != 0:
        print(f"FAIL: exit {proc.returncode}: {' '.join(argv)}")
    return proc.returncode


def run_pytest_suite(label: str, targets: list[str]) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = label.replace("/", "_")
    xml = OUT_DIR / f"tb_selfcheck_{safe}.xml"
    argv = [
        sys.executable,
        "-P",
        "-m",
        "pytest",
        *targets,
        "-q",
        f"--junitxml={xml}",
    ]
    rc = run_or_fail(argv)
    if not xml.is_file():
        print(f"FAIL: {label}: pytest wrote no junit xml")
        return 1
    counts = parse_junit_counts(xml)
    print(
        f"tb-selfcheck counts {label}: collected={counts['collected']} "
        f"passed={counts['passed']} failed={counts['failed']} "
        f"skipped={counts['skipped']}"
    )
    if pytest_skip_is_fail(counts):
        for name in counts["skip_names"]:
            print(f"FAIL: {label} skipped {name}")
        for name in counts["fail_names"]:
            print(f"FAIL: {label} failed {name}")
        return 1
    return rc


def main() -> int:
    print_tool_versions(["python", "icarus", "verilator"])
    try:
        import pytest  # noqa: F401
    except ImportError:
        print(
            f"ERROR: {sys.executable} has no pytest; "
            "do not run tb-selfcheck under .pycircuit-venv"
        )
        return 1
    missing = required_sim_tools()
    if missing:
        print(
            "ERROR: missing "
            + ", ".join(missing)
            + " (install TOOLCHAIN.lock pins; Verilator is required so "
            "tb/cmn PRODUCT+HOOKS RTL sim cannot skip)"
        )
        return 1

    pytest_files = discover_pytest_files()
    model_dir = REPO_ROOT / "model"
    makefiles = discover_cocotb_makefiles()
    print("tb-selfcheck discovery:")
    print(f"  pytest files under tb/: {[rel(p) for p in pytest_files] or '[]'}")
    print(f"  model/: {'yes' if model_dir.is_dir() else 'absent'}")
    print(
        "  cocotb Makefiles: "
        + (
            ", ".join(f"{rel(d)}:{t}" for d, t in makefiles)
            if makefiles
            else "[]"
        )
    )
    print("  D10 *_tb.v: not run")

    fail = 0
    if model_dir.is_dir():
        fail |= run_pytest_suite("model/tests", [str(model_dir)])
    else:
        print("NOTE: model/ not present; skip top-level golden pytest")

    grouped: dict[str, list[Path]] = {}
    for path in pytest_files:
        grouped.setdefault(suite_label(path), []).append(path)
    if not grouped:
        print("NOTE: no non-cocotb pytest files under tb/")
    for label in ("tb/cmn", "tb/models", "tb/other"):
        files = grouped.get(label) or []
        if not files:
            continue
        fail |= run_pytest_suite(label, [str(p) for p in files])

    if not makefiles:
        print("NOTE: no tb/Makefile (or tb/*/Makefile) with selfcheck-both/selfcheck")
    for directory, target in makefiles:
        fail |= run_or_fail(["make", "-C", str(directory), target, "SIM=icarus"])

    if fail:
        print("tb-selfcheck: FAIL")
        return 1
    print("tb-selfcheck: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
