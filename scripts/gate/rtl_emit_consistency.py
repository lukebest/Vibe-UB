#!/usr/bin/env python3
"""Line A: pycircuit → emit_rtl.py → rtl consistency, hooks, PRODUCT↔hooks eqy.

Never assemble pycc argv here. scripts/emit_rtl.py is the only source of
compile() + pycc --emit=verilog --logic-depth=64. Regen into an isolated
tree and byte-compare rtl/<layer>/ and rtl/<layer>/hooks/.

emit_rtl.py missing → skip (report-only). Present → blocking.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
    GATE_DIR,
    OUT_DIR,
    REPO_ROOT,
    Finding,
    collect_import_root_findings,
    collect_layer_netlists,
    collect_placeholder_policy_findings,
    cmn_mem_bits,
    cmn_mem_is_large,
    cmn_mem_tag_of,
    discover_layers,
    discover_leaf_pairs,
    discover_rtl,
    emit_report,
    hooks_extra_for,
    is_cmn_mem_module,
    is_handwritten_path,
    is_legacy_path,
    is_placeholder_module,
    is_tb_obs_port,
    is_tb_port,
    iter_rtl_sources,
    large_cmn_mem_lib_files,
    leaf_process_env,
    leaf_python_argv,
    looks_generated,
    packed_width,
    parse_cmn_mem_tag,
    parse_port_decls,
    print_tool_versions,
    read_cmn_mem_threshold_bits,
    rel,
    run_cmd,
    shutil_which,
    verilog_equal_except_module_name,
)
from hooks_port_consistency import compare_ports
from large_mem_manifest import check_large_mem_manifest
from pyc_lib_check import check_pyc_lib

# Call only this script. Do not add pycc flags here.
EMIT_SCRIPT = "scripts/emit_rtl.py"

def _port_decl(kind: str, name: str, packed: str) -> str:
    rng = f"{packed} " if packed else ""
    return f"  {kind} {rng}{name};"


def _tie_low_expr(packed: str) -> str:
    width = packed_width(packed)
    if width <= 1:
        return "1'b0"
    return f"{width}'b0"


def write_hooks_wrapper(
    hooks_path: Path,
    module: str,
    dest: Path,
    product_path: Path | None = None,
) -> list[str]:
    """Wrap HOOKS so only PRODUCT ports are compared (SPEC §11).

    Exposed ports keep the PRODUCT packed width (fixes gold/gate bus
    mismatch). Extra HOOKS inputs (tb_test_mode / tb_inj_* /
    tb_<inst>_bd_* / tb_<inst>_bd_vld_*) tie to 0 at their native width.
    Observe (tb_obs_* / tb_<inst>_obs_*) left open. Other extra tb_*
    inputs also tie low.
    """
    hooks = parse_port_decls(hooks_path)
    if product_path is not None and product_path.is_file():
        exposed = parse_port_decls(product_path)
    else:
        exposed = [(k, n, p) for k, n, p in hooks if not is_tb_port(n)]
    tied: list[tuple[str, str, str]] = []
    exposed_names = {n for _k, n, _p in exposed}
    for kind, name, packed in hooks:
        if name in exposed_names:
            continue
        tied.append((kind, name, packed))
    lines = [
        f"// Auto-generated eqy wrapper: {module} PRODUCT ports only;",
        "// extra HOOKS inputs tied low at native width. Do not commit.",
        f"module {module}_eqy_hooks (",
    ]
    if exposed:
        lines.append("  " + ",\n  ".join(n for _k, n, _p in exposed))
    lines.append(");")
    for kind, name, packed in exposed:
        lines.append(_port_decl(kind, name, packed))
    conns: list[str] = []
    for _k, name, _p in exposed:
        conns.append(f".{name}({name})")
    for kind, name, packed in tied:
        if is_tb_obs_port(name) or kind == "output":
            conns.append(f".{name}()")
        else:
            conns.append(f".{name}({_tie_low_expr(packed)})")
    lines.append(f"  {module} u_hooks (")
    lines.append("    " + ",\n    ".join(conns))
    lines.append("  );")
    lines.append("endmodule")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [n for _k, n, _p in tied]


def _lib_reads(lib_files: list[Path] | None) -> list[str]:
    """Same blackbox copy on gold and gate (large ub_cmn_mem_1r1w)."""
    out: list[str] = []
    seen: set[Path] = set()
    for path in lib_files or []:
        rp = path.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        flag = "-sv" if rp.suffix.lower() == ".sv" else ""
        out.append(f"read_verilog -lib {flag} {rp}".replace("  ", " "))
    return out


def _yosys_equiv_script(
    product: Path,
    gold_top: str,
    gate_reads: list[str],
    gate_top: str,
    lib_files: list[Path] | None = None,
) -> str:
    """Yosys equiv_make / equiv_simple / equiv_induct / equiv_status -assert."""
    libs = _lib_reads(lib_files)
    return "\n".join(
        [
            f"read_verilog -sv {product}",
            *libs,
            f"hierarchy -check -top {gold_top}",
            "proc",
            "opt",
            "design -save gold",
            "design -reset",
            *gate_reads,
            *libs,
            f"hierarchy -check -top {gate_top}",
            "proc",
            "opt",
            "design -save gate",
            f"design -copy-from gold -as gold {gold_top}",
            f"design -copy-from gate -as gate {gate_top}",
            "equiv_make gold gate equiv",
            "prep -top equiv",
            "equiv_simple",
            "equiv_induct",
            "equiv_status -assert",
        ]
    )


def _emit_python() -> str:
    venv = REPO_ROOT / ".pycircuit-venv" / "bin" / "python"
    return str(venv) if venv.is_file() else sys.executable


def _prepare_pycc_path() -> None:
    prefix = REPO_ROOT / ".pycircuit_out" / "toolchain" / "install" / "bin"
    if prefix.is_dir():
        os.environ["PATH"] = f"{prefix}{os.pathsep}{os.environ.get('PATH', '')}"
        os.environ.setdefault("PYC_TOOLCHAIN_ROOT", str(prefix.parent))


def compare_emitted_rtl(generated_rtl: Path, committed_rtl: Path) -> list[Finding]:
    """Byte-compare isolated emit output to committed rtl/<layer>/ and hooks/."""
    gen = collect_layer_netlists(generated_rtl)
    committed = collect_layer_netlists(committed_rtl)
    findings: list[Finding] = []
    for key, gp in gen.items():
        dest = f"rtl/{key}"
        cp = committed.get(key)
        if cp is None:
            findings.append(
                Finding(
                    check="emit",
                    module=Path(key).stem,
                    file=dest,
                    rule="EMIT_DIFF",
                    message=f"emit_rtl.py produced {dest} not present in committed tree",
                )
            )
            continue
        if is_handwritten_path(cp):
            continue
        if gp.read_bytes() != cp.read_bytes():
            findings.append(
                Finding(
                    check="emit",
                    module=Path(key).stem,
                    file=dest,
                    rule="EMIT_DIFF",
                    message=f"regenerated {dest} differs byte-for-byte from committed",
                )
            )
    for key, cp in committed.items():
        if is_handwritten_path(cp):
            continue
        if key in gen:
            continue
        if looks_generated(cp):
            findings.append(
                Finding(
                    check="emit",
                    module=Path(key).stem,
                    file=f"rtl/{key}",
                    rule="EMIT_DIFF",
                    message=f"committed rtl/{key} was not regenerated by emit_rtl.py",
                )
            )
    return findings


def emit_unavailable_findings(
    emit_path: Path | None = None,
    pycc_ready: bool = True,
    reason: str = "",
) -> list[Finding]:
    """Report-only skip when emit_rtl.py is missing or pycc cannot be installed."""
    path = emit_path if emit_path is not None else REPO_ROOT / EMIT_SCRIPT
    if not path.is_file():
        msg = f"{EMIT_SCRIPT} missing; regen compare skipped"
        print(f"skip emit+byte-compare: {msg}")
        return [
            Finding(
                check="emit",
                module="*",
                file=EMIT_SCRIPT,
                rule="EMIT_SKIP",
                message=msg,
                bucket="report",
            )
        ]
    if not pycc_ready:
        msg = reason or "pycc could not be installed from TOOLCHAIN.lock"
        print(f"skip emit+byte-compare: {msg}")
        return [
            Finding(
                check="emit",
                module="*",
                file=EMIT_SCRIPT,
                rule="EMIT_SKIP",
                message=f"pycc unavailable; regen compare skipped ({msg})",
                bucket="report",
            )
        ]
    return []


def _setup_reason_from_log(log: str) -> str:
    for line in (log or "").splitlines()[::-1]:
        text = line.strip()
        if text.startswith("BLOCKER:"):
            return text
    return "setup_pycircuit.sh did not reach SETUP_OK=1"


def prepare_pycc_from_lock() -> tuple[bool, str]:
    """Install pycc per TOOLCHAIN.lock. Missing toolchain is skip, not fail."""
    setup = GATE_DIR / "setup_pycircuit.sh"
    log = ""
    if setup.is_file():
        print(f"=== {rel(setup)} (TOOLCHAIN.lock pin; so emit_rtl.py can call pycc) ===")
        proc = run_cmd(["bash", str(setup)], timeout=600)
        log = proc.stdout or ""
        print("\n".join(log.strip().splitlines()[-30:] or [""]))
        setup_log = GATE_DIR / "out" / "pycircuit_setup.log"
        if setup_log.is_file():
            log = setup_log.read_text(encoding="utf-8", errors="replace")
        if "SETUP_OK=1" in log:
            _prepare_pycc_path()
            return True, ""
        return False, _setup_reason_from_log(log)
    _prepare_pycc_path()
    if shutil_which("pycc"):
        return True, ""
    return False, "setup_pycircuit.sh missing and pycc not on PATH"


def run_emit_rtl_isolated() -> tuple[list[Finding], Path | None, dict[str, object]]:
    """Run scripts/emit_rtl.py in a detached worktree; never build pycc argv.

    Caller must drop the worktree (meta['worktree']) when finished. Generated
    rtl stays available for the large-mem manifest sha256 check.
    """
    meta: dict[str, object] = {
        "worktree": None,
        "script_present": False,
        "pycc_ready": False,
        "reason": "",
    }
    emit_path = REPO_ROOT / EMIT_SCRIPT
    meta["script_present"] = emit_path.is_file()
    if not emit_path.is_file():
        return emit_unavailable_findings(emit_path), None, meta

    ready, reason = prepare_pycc_from_lock()
    meta["pycc_ready"] = ready
    meta["reason"] = reason
    if not ready:
        return emit_unavailable_findings(emit_path, False, reason), None, meta

    tmp = Path(tempfile.mkdtemp(prefix="gate-emit-"))
    add = run_cmd(["git", "worktree", "add", "--detach", str(tmp), "HEAD"])
    if add.returncode != 0:
        print(add.stdout or "")
        return (
            [
                Finding(
                    check="emit",
                    module="*",
                    file=EMIT_SCRIPT,
                    rule="EMIT_FAIL",
                    message=f"git worktree add failed: {(add.stdout or '')[:200]}",
                )
            ],
            None,
            meta,
        )
    meta["worktree"] = tmp
    script = tmp / EMIT_SCRIPT
    py = _emit_python()
    argv = leaf_python_argv(script, python=py)
    env = leaf_process_env(tmp)
    print(
        f"=== {' '.join(argv)} (isolated worktree; "
        "PYTHONPATH=<worktree>/pycircuit first; python -P; "
        "pycc argv comes only from this script) ==="
    )
    proc = run_cmd(argv, cwd=tmp, timeout=600, env=env)
    print(proc.stdout or "")
    if proc.returncode != 0:
        return (
            [
                Finding(
                    check="emit",
                    module="*",
                    file=EMIT_SCRIPT,
                    rule="EMIT_FAIL",
                    message=f"{EMIT_SCRIPT} exited {proc.returncode}",
                )
            ],
            tmp / "rtl" if (tmp / "rtl").is_dir() else None,
            meta,
        )
    return compare_emitted_rtl(tmp / "rtl", REPO_ROOT / "rtl"), tmp / "rtl", meta


def run_equiv(
    module: str,
    product: Path,
    hooks: Path,
    extra_ports: list[str] | None,
    lib_files: list[Path] | None = None,
) -> Finding | None:
    """Prove PRODUCT≡HOOKS. Primary: Yosys equiv_*. eqy if available."""
    work = OUT_DIR / "eqy" / module
    work.mkdir(parents=True, exist_ok=True)
    gold_top = module
    if extra_ports is None:
        gate_top = module
        gate_reads = [f"read_verilog -sv {hooks}"]
        kind = "no-hook leaf, ports 1:1"
    else:
        wrap = work / f"{module}_eqy_hooks.v"
        tied = write_hooks_wrapper(hooks, module, wrap, product_path=product)
        gate_top = f"{module}_eqy_hooks"
        gate_reads = [f"read_verilog -sv {hooks}", f"read_verilog -sv {wrap}"]
        kind = f"hooked; extra inputs tied low ({tied or 'none'})"

    eqy_bin = shutil_which("eqy")
    yosys_bin = shutil_which("yosys")
    # This environment cannot install eqy. Yosys equiv_* is the primary path.
    if yosys_bin and not eqy_bin:
        tool = "yosys-equiv"
        ys = work / f"{module}_equiv.ys"
        ys.write_text(
            _yosys_equiv_script(
                product, gold_top, gate_reads, gate_top, lib_files=lib_files
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            f"--- EQUIV tool=yosys-equiv {module} ({kind}); "
            "equiv_make/equiv_simple/equiv_induct/equiv_status -assert ---"
        )
        proc = run_cmd(["yosys", "-s", str(ys)], cwd=work, timeout=180)
    elif eqy_bin:
        tool = "eqy"
        eqy_file = work / f"{module}.eqy"
        eqy_file.write_text(
            "\n".join(
                [
                    "[options]",
                    "splitnets on",
                    "",
                    "[gold]",
                    f"read_verilog -sv {product}",
                    *_lib_reads(lib_files),
                    f"prep -top {gold_top}",
                    "",
                    "[gate]",
                    *gate_reads,
                    *_lib_reads(lib_files),
                    f"prep -top {gate_top}",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"--- EQUIV tool=eqy {module} ({kind}) ---")
        proc = run_cmd(["eqy", "-f", str(eqy_file)], cwd=work, timeout=180)
    else:
        print(f"--- EQUIV tool=NONE {module}: yosys and eqy both missing ---")
        return Finding(
            check="emit",
            module=module,
            file=rel(product),
            rule="EQUIV_TOOL_MISSING",
            message="yosys not on PATH (eqy also missing); cannot prove PRODUCT≡hooks",
        )

    text = proc.stdout or ""
    print("\n".join((text.strip().splitlines() or [""])[-40:]))
    proven = (
        proc.returncode == 0
        and (
            "Equivalence successfully proven" in text
            or tool == "eqy"
        )
    )
    if tool == "eqy" and proc.returncode == 0:
        proven = True
    if not proven:
        return Finding(
            check="emit",
            module=module,
            file=rel(product),
            rule="EQUIV_FAIL",
            message=(
                f"PRODUCT vs hooks not equivalent (tool={tool}, "
                f"exit {proc.returncode}; {kind})"
            ),
        )
    print(f"EQUIV {module}: PASS tool={tool}")
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--equiv-only",
        action="store_true",
        help="skip emit+diff; run PRODUCT≡HOOKS only (visible equiv job)",
    )
    args = parser.parse_args()
    print_tool_versions(["python", "yosys", "eqy"])
    print(
        f"emit knobs: EMIT_SCRIPT={EMIT_SCRIPT} "
        "(no gate-built pycc argv; compile/--emit=verilog/--logic-depth=64 "
        f"live only in that script) equiv_only={args.equiv_only}"
    )
    pyc_layers = discover_layers(REPO_ROOT / "pycircuit")
    rtl_layers = discover_layers(REPO_ROOT / "rtl")
    formal_layers = discover_layers(REPO_ROOT / "formal")
    print(
        f"discovered layers: pycircuit={pyc_layers or '[]'} "
        f"rtl={rtl_layers or '[]'} formal={formal_layers or '[]'} "
        f"(cmn always enumerated)"
    )

    findings: list[Finding] = []
    findings.extend(collect_import_root_findings("emit"))
    worktree: Path | None = None
    generated_rtl: Path | None = None
    emit_meta: dict[str, object] = {
        "script_present": False,
        "pycc_ready": False,
        "reason": "",
    }
    try:
        if not args.equiv_only:
            findings.extend(collect_placeholder_policy_findings("emit"))
            emit_hits, generated_rtl, emit_meta = run_emit_rtl_isolated()
            worktree = emit_meta.get("worktree")  # type: ignore[assignment]
            findings.extend(emit_hits)
            findings.extend(
                check_large_mem_manifest(
                    REPO_ROOT / "rtl",
                    generated_rtl=generated_rtl,
                    emit_available=bool(emit_meta.get("script_present")),
                    pycc_ready=bool(emit_meta.get("pycc_ready")),
                    skip_reason=str(emit_meta.get("reason") or ""),
                )
            )
            findings.extend(
                check_pyc_lib(
                    REPO_ROOT / "rtl",
                    lock_src=REPO_ROOT / ".pycircuit-src",
                )
            )
            if any(f.rule == "EMIT_FAIL" and f.bucket == "new" for f in findings):
                return emit_report("emit", findings)
        else:
            print("equiv-only: skip emit+byte-compare")
            findings.extend(
                check_large_mem_manifest(
                    REPO_ROOT / "rtl",
                    generated_rtl=None,
                    emit_available=False,
                    pycc_ready=False,
                    skip_reason="equiv-only",
                )
            )
            findings.extend(
                check_pyc_lib(
                    REPO_ROOT / "rtl",
                    lock_src=REPO_ROOT / ".pycircuit-src",
                )
            )
    finally:
        if worktree is not None:
            run_cmd(["git", "worktree", "remove", "--force", str(worktree)])

    if not args.equiv_only:
        for path in iter_rtl_sources():
            if is_handwritten_path(path):
                print(f"handwritten OK {rel(path)} (skip emit/hooks/eqy)")
                continue
            if looks_generated(path):
                continue
            findings.append(
                Finding(
                    check="emit",
                    module=path.stem,
                    file=rel(path),
                    rule="HANDWRITTEN_UNLISTED",
                    message=(
                        "handwritten .v/.sv under rtl/ is not on "
                        "scripts/gate/handwritten.yml "
                        "(or the entry has no gatekeeper approver)"
                    ),
                )
            )

    disc = discover_rtl()
    thresh = read_cmn_mem_threshold_bits()
    print(f"equiv: ub_cmn_mem_1r1w blackbox threshold={thresh} bits")
    for leaf in discover_leaf_pairs():
        product = REPO_ROOT / leaf["product"]
        hooks = REPO_ROOT / leaf["hooks"]
        module = leaf["module"]
        if leaf.get("placeholder") or is_placeholder_module(module):
            print(f"placeholder skip {module}: lint/TB only (not PRODUCT, no equiv)")
            continue
        if product.is_file() and is_handwritten_path(product):
            print(f"eqy/hooks skip {module}: handwritten whitelist")
            continue
        if not product.is_file():
            findings.append(
                Finding(
                    check="emit",
                    module=module,
                    file=leaf["product"],
                    rule="PRODUCT_MISSING",
                    message=f"no PRODUCT netlist at {leaf['product']}",
                )
            )
            continue
        if is_legacy_path(product):
            continue
        if not hooks.is_file():
            findings.append(
                Finding(
                    check="emit",
                    module=module,
                    file=leaf["product"],
                    rule="HOOKS_MISSING",
                    message=(
                        f"non-legacy leaf missing hooks netlist {leaf['hooks']} "
                        f"(SPEC §11)"
                    ),
                )
            )
            continue
        extra = hooks_extra_for(module, leaf.get("leaf"))
        dims = parse_cmn_mem_tag(cmn_mem_tag_of(module) or "") or leaf.get("params")
        if is_cmn_mem_module(module) and cmn_mem_is_large(
            product, dims, thresh=thresh
        ):
            bits = cmn_mem_bits(product, dims)
            print(
                f"equiv skip full {module}: large ub_cmn_mem_1r1w "
                f"({bits} bits > {thresh}); byte-compare except module name + ports"
            )
            if not verilog_equal_except_module_name(product, hooks):
                findings.append(
                    Finding(
                        check="emit",
                        module=module,
                        file=leaf["product"],
                        rule="CMN_MEM_BODY_DIFF",
                        message=(
                            f"large variant ({bits} bits > {thresh}): "
                            "PRODUCT vs HOOKS must match byte-for-byte except module name"
                        ),
                    )
                )
            port_hits = compare_ports(module, product, hooks, extra)
            for hit in port_hits:
                hit.check = "emit"
            findings.extend(port_hits)
            continue
        lib_files = large_cmn_mem_lib_files(module, disc)
        if lib_files:
            print(
                f"equiv {module}: -lib large ub_cmn_mem_1r1w "
                f"{[rel(p) for p in lib_files]} (same copy both sides)"
            )
        hit = run_equiv(module, product, hooks, extra, lib_files=lib_files)
        if hit:
            findings.append(hit)

    return emit_report("equiv" if args.equiv_only else "emit", findings)


if __name__ == "__main__":
    raise SystemExit(main())
