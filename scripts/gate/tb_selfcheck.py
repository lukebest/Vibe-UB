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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
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


def run_or_fail(argv: list[str], cwd: Path | None = None) -> int:
    print(f"=== {' '.join(argv)} ===")
    proc = run_cmd(argv, cwd=cwd, env=leaf_process_env())
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.returncode != 0:
        print(f"FAIL: exit {proc.returncode}: {' '.join(argv)}")
    return proc.returncode


def main() -> int:
    print_tool_versions(["python", "icarus"])
    if not shutil_which("iverilog"):
        print("ERROR: iverilog is not on PATH; Icarus is the tb-selfcheck gate (D7)")
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
        fail |= run_or_fail(
            [sys.executable, "-P", "-m", "pytest", str(model_dir), "-q"]
        )
    else:
        print("NOTE: model/ not present; skip top-level golden pytest")

    if pytest_files:
        fail |= run_or_fail(
            [
                sys.executable,
                "-P",
                "-m",
                "pytest",
                *[str(p) for p in pytest_files],
                "-q",
            ]
        )
    else:
        print("NOTE: no non-cocotb pytest files under tb/")

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
