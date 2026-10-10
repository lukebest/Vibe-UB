#!/usr/bin/env python3
"""rtl/pyc_lib vs locked pyCircuit; no stray pyc_* primitives elsewhere.

rtl/pyc_lib/ lands with #21. If the directory is missing, report skip
(do not fail). If it exists, byte-compare each pyc_*.v against the
TOOLCHAIN.lock pin of lukebest/pyCircuit. A pyc_* primitive anywhere
else under rtl/ is blocking.

This PR does not add or remove scripts/gate/handwritten.yml pyc_reg
entries — that is #21's change.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import Finding, RTL_SOURCE_SUFFIXES, rel

PYC_LIB_DIRNAME = "pyc_lib"


def _is_pyc_primitive(path: Path) -> bool:
    return path.name.startswith("pyc_") and path.suffix.lower() in RTL_SOURCE_SUFFIXES


def _in_pyc_lib(path: Path, rtl_root: Path) -> bool:
    try:
        rel_to_rtl = path.resolve().relative_to(rtl_root.resolve())
    except ValueError:
        return False
    return rel_to_rtl.parts[:1] == (PYC_LIB_DIRNAME,)


def collect_stray_pyc_primitives(rtl_root: Path) -> list[Path]:
    if not rtl_root.is_dir():
        return []
    stray: list[Path] = []
    for path in sorted(rtl_root.rglob("pyc_*")):
        if not path.is_file() or not _is_pyc_primitive(path):
            continue
        if _in_pyc_lib(path, rtl_root):
            continue
        stray.append(path)
    return stray


def locked_pyc_primitives(lock_src: Path) -> dict[str, Path]:
    """Map basename → first pyc_*.v under the locked pyCircuit clone."""
    out: dict[str, Path] = {}
    if not lock_src.is_dir():
        return out
    for path in sorted(lock_src.rglob("pyc_*")):
        if path.is_file() and _is_pyc_primitive(path):
            out.setdefault(path.name, path)
    return out


def check_pyc_lib(
    rtl_root: Path,
    lock_src: Path | None = None,
    check: str = "emit",
) -> list[Finding]:
    findings: list[Finding] = []
    for path in collect_stray_pyc_primitives(rtl_root):
        findings.append(
            Finding(
                check=check,
                module=path.stem,
                file=rel(path),
                rule="PYC_PRIMITIVE_STRAY",
                message=(
                    f"{path.name} is a pyCircuit primitive; only rtl/pyc_lib/ "
                    "may contain pyc_* (locked pin, byte-identical)"
                ),
            )
        )

    pyc_lib = rtl_root / PYC_LIB_DIRNAME
    if not pyc_lib.is_dir():
        findings.append(
            Finding(
                check=check,
                module="*",
                file="rtl/pyc_lib",
                rule="PYC_LIB_SKIP",
                message=(
                    "rtl/pyc_lib/ is not on this tree (lands with #21); "
                    "byte-compare skipped"
                ),
                bucket="report",
            )
        )
        return findings

    if lock_src is None or not lock_src.is_dir():
        findings.append(
            Finding(
                check=check,
                module="*",
                file="rtl/pyc_lib",
                rule="PYC_LIB_SKIP",
                message=(
                    "rtl/pyc_lib/ present but locked pyCircuit source is not "
                    "available; byte-compare skipped"
                ),
                bucket="report",
            )
        )
        return findings

    locked = locked_pyc_primitives(lock_src)
    for path in sorted(pyc_lib.iterdir()):
        if not path.is_file() or not _is_pyc_primitive(path):
            continue
        gold = locked.get(path.name)
        if gold is None:
            findings.append(
                Finding(
                    check=check,
                    module=path.stem,
                    file=rel(path),
                    rule="PYC_LIB_UNKNOWN",
                    message=(
                        f"{path.name} is not a pyc_* primitive in the locked "
                        "pyCircuit tree"
                    ),
                )
            )
            continue
        if path.read_bytes() != gold.read_bytes():
            findings.append(
                Finding(
                    check=check,
                    module=path.stem,
                    file=rel(path),
                    rule="PYC_LIB_DIFF",
                    message=(
                        f"{rel(path)} differs byte-for-byte from locked "
                        f"pyCircuit {gold.as_posix()}"
                    ),
                )
            )
    return findings
