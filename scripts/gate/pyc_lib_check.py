#!/usr/bin/env python3
"""rtl/pyc_lib vs locked pyCircuit; no stray pyc_* primitives elsewhere.

rtl/pyc_lib/ lands with #21. If the directory is missing, report skip
(do not fail). If it exists, byte-compare each pyc_*.v against the
TOOLCHAIN.lock pin of lukebest/pyCircuit. A pyc_* primitive anywhere
else under rtl/ is blocking.

GATE-PYCLIB-SINGLE (report-only until #47 is on main): no second copy of a
rtl/pyc_lib module/file, and no script may fetch rtl/pyc_lib from another
ref or toolchain path.

This PR does not add or remove scripts/gate/handwritten.yml pyc_reg
entries — that is #21's change.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
    LOCK_SCAN_SKIP_DIRS,
    REPO_ROOT,
    RTL_SOURCE_SUFFIXES,
    Finding,
    rel,
    run_cmd,
)
from private_leaves import load_private_config

PYC_LIB_DIRNAME = "pyc_lib"
FALLBACK_PYCLIB_NAMES = frozenset({"pyc_reg"})
# Report-only while this exact path exists on origin/main. Remove after #5.
PYCLIB_COPY_ALLOWLIST = ("rtl/common/pyc_reg.v",)
ALLOWLIST_NOTE = "remove after #5"
MODULE_RE = re.compile(
    r"^\s*module\s+([A-Za-z_][A-Za-z0-9_]*)\b",
    re.M,
)
GIT_SHOW_PYCLIB_RE = re.compile(
    r"\bgit\s+show\b[^\n]*:rtl/pyc_lib\b",
    re.I,
)
GIT_CHECKOUT_PYCLIB_RE = re.compile(
    r"\bgit\s+checkout\b[^\n]*--\s+rtl/pyc_lib\b",
    re.I,
)
GIT_FETCH_PYCLIB_RE = re.compile(
    r"\bgit\s+fetch\b[\s\S]{0,240}rtl/pyc_lib\b",
    re.I,
)
TOOLCHAIN_COPY_RE = re.compile(
    r"(?:site-packages|TOOLCHAIN(?:\.lock)?)[^\n]{0,160}pyc_reg\.v"
    r"|pyc_reg\.v[^\n]{0,160}(?:site-packages|TOOLCHAIN(?:\.lock)?)",
    re.I,
)
FETCH_SCRIPT_SUFFIXES = {".sh", ".py", ".sby"}
FETCH_MAKE_NAMES = frozenset({"makefile", "gnumakefile"})
SELFTEST_NAME_RE = re.compile(r"selftest", re.I)
PYCLIB_SINGLE_MAX_READ = 2_000_000


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
        repo = rtl_root.parent if rtl_root.name == "rtl" else rtl_root
        if main_has_pyc_lib(repo):
            findings.append(
                Finding(
                    check=check,
                    module="*",
                    file="rtl/pyc_lib",
                    rule="PYC_LIB_MISSING",
                    message=(
                        "rtl/pyc_lib/ is required once it exists on origin/main "
                        "(#21); restore the locked primitive tree"
                    ),
                )
            )
        else:
            findings.append(
                Finding(
                    check=check,
                    module="*",
                    file="rtl/pyc_lib",
                    rule="PYC_LIB_SKIP",
                    message=(
                        "rtl/pyc_lib/ is not on this tree or origin/main "
                        "(lands with #21); byte-compare skipped"
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


def _git_path_on_main(root: Path, rel_posix: str) -> bool:
    proc = run_cmd(["git", "cat-file", "-e", f"origin/main:{rel_posix}"], cwd=root)
    return proc.returncode == 0


def main_has_pyc_lib(root: Path) -> bool:
    flag = load_private_config(root).get("pyc_lib_on_main")
    if flag is True or flag is False:
        return bool(flag)
    return _git_path_on_main(root, "rtl/pyc_lib")


def main_has_path(root: Path, rel_posix: str) -> bool:
    key = "pyclib_copy_on_main"
    cfg = load_private_config(root).get(key)
    if isinstance(cfg, dict) and rel_posix in cfg:
        return bool(cfg[rel_posix])
    return _git_path_on_main(root, rel_posix)


def stale_pyclib_copy_allowlist(root: Path) -> list[str]:
    """Allowlist paths that origin/main no longer has — delete the entry."""
    return [p for p in PYCLIB_COPY_ALLOWLIST if not main_has_path(root, p)]


def pyclib_single_required(root: Path) -> bool:
    """Blocking once #47 is on main, or yml override."""
    flag = load_private_config(root).get("pyclib_single_required")
    if flag is True or flag is False:
        return bool(flag)
    proc = run_cmd(
        ["git", "show", "origin/main:docs/rules/verif_gate.md"],
        cwd=root,
    )
    if proc.returncode != 0:
        return False
    return "GATE-PYCLIB-SINGLE" in (proc.stdout or "")


def _norm_rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _in_rtl_pyc_lib(rel_posix: str) -> bool:
    return rel_posix == "rtl/pyc_lib" or rel_posix.startswith("rtl/pyc_lib/")


def _is_gate_selftest_fixture(rel_posix: str) -> bool:
    parts = rel_posix.split("/")
    if len(parts) >= 2 and parts[0] == "scripts" and parts[1] == "gate":
        name = parts[-1]
        if name == "pyc_lib_check.py" or SELFTEST_NAME_RE.search(name):
            return True
        if "fixtures" in parts:
            return True
    return False


def _iter_repo_files(root: Path) -> list[Path]:
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


def pyclib_catalog(rtl_root: Path) -> tuple[set[str], set[str]]:
    """Return (module names, basenames) defined under rtl/pyc_lib/."""
    names: set[str] = set(FALLBACK_PYCLIB_NAMES)
    basenames: set[str] = {f"{n}.v" for n in FALLBACK_PYCLIB_NAMES}
    pyc_lib = rtl_root / PYC_LIB_DIRNAME
    if not pyc_lib.is_dir():
        return names, basenames
    for path in sorted(pyc_lib.iterdir()):
        if not path.is_file() or not _is_pyc_primitive(path):
            continue
        basenames.add(path.name)
        names.add(path.stem)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        names.update(MODULE_RE.findall(text))
    return names, basenames


def check_pyclib_copies(root: Path, rtl_root: Path, bucket: str) -> list[Finding]:
    modules, basenames = pyclib_catalog(rtl_root)
    findings: list[Finding] = []
    for path in _iter_repo_files(root):
        rel_posix = _norm_rel(root, path)
        if _in_rtl_pyc_lib(rel_posix) or _is_gate_selftest_fixture(rel_posix):
            continue
        reasons: list[str] = []
        if path.name in basenames:
            reasons.append(f"named like rtl/pyc_lib/{path.name}")
        if path.suffix.lower() in RTL_SOURCE_SUFFIXES:
            try:
                if path.stat().st_size > PYCLIB_SINGLE_MAX_READ:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            defined = sorted(set(MODULE_RE.findall(text)) & modules)
            if defined:
                reasons.append("defines module " + "/".join(defined))
        if not reasons:
            continue
        copy_bucket = bucket
        note = ""
        if rel_posix in PYCLIB_COPY_ALLOWLIST and main_has_path(root, rel_posix):
            copy_bucket = "report"
            note = f" ({ALLOWLIST_NOTE})"
        findings.append(
            Finding(
                check="emit",
                module=path.stem,
                file=rel_posix,
                rule="PYCLIB_COPY",
                message=(
                    "second copy of an rtl/pyc_lib primitive ("
                    + "; ".join(reasons)
                    + "); keep the single copy in rtl/pyc_lib/"
                    + note
                ),
                bucket=copy_bucket,
                severity="error" if copy_bucket == "new" else "warning",
            )
        )
    findings.sort(key=lambda f: f.file)
    return findings


def _fetch_reason(text: str) -> str | None:
    if GIT_SHOW_PYCLIB_RE.search(text):
        return "git show <ref>:rtl/pyc_lib"
    if GIT_CHECKOUT_PYCLIB_RE.search(text):
        return "git checkout <ref> -- rtl/pyc_lib"
    if GIT_FETCH_PYCLIB_RE.search(text):
        return "git fetch + rtl/pyc_lib"
    if TOOLCHAIN_COPY_RE.search(text):
        return "copy pyc_reg.v from site-packages/toolchain"
    return None


def check_pyclib_fetches(root: Path, bucket: str) -> list[Finding]:
    findings: list[Finding] = []
    for path in _iter_repo_files(root):
        rel_posix = _norm_rel(root, path)
        if _is_gate_selftest_fixture(rel_posix):
            continue
        name = path.name
        if path.suffix.lower() not in FETCH_SCRIPT_SUFFIXES and name.lower() not in FETCH_MAKE_NAMES:
            continue
        try:
            if path.stat().st_size > PYCLIB_SINGLE_MAX_READ:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        reason = _fetch_reason(text)
        if not reason:
            continue
        findings.append(
            Finding(
                check="emit",
                module="*",
                file=rel_posix,
                rule="PYCLIB_FETCH",
                message=(
                    "script fetches rtl/pyc_lib from another ref or toolchain "
                    f"({reason}); use the committed rtl/pyc_lib/ tree"
                ),
                bucket=bucket,
                severity="error" if bucket == "new" else "warning",
            )
        )
    findings.sort(key=lambda f: f.file)
    return findings


def check_pyclib_single(
    root: Path | None = None,
    rtl_root: Path | None = None,
) -> list[Finding]:
    """GATE-PYCLIB-SINGLE: one committed pyc_lib, no out-of-tree fetch."""
    root = root or REPO_ROOT
    rtl_root = rtl_root or (root / "rtl")
    bucket = "new" if pyclib_single_required(root) else "report"
    findings = check_pyclib_copies(root, rtl_root, bucket)
    findings.extend(check_pyclib_fetches(root, bucket))
    return findings
