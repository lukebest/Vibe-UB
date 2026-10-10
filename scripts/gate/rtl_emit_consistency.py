#!/usr/bin/env python3
"""Line A: pycircuit → emit → rtl consistency, hooks presence, PRODUCT↔hooks eqy.

Architecture-confirmed layout (will be SPEC §2.2 / §11):
  pycircuit/<layer>/          source (including pycircuit/csr/)
  scripts/emit_rtl.py         emit
  rtl/<layer>/<module>.v      PRODUCT
  rtl/<layer>/hooks/<module>.v
  rtl/                        generated .v only (plus whitelist cells)

Skip the whole job when emit_rtl.py is missing.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
    OUT_DIR,
    REPO_ROOT,
    Finding,
    discover_layers,
    discover_leaf_pairs,
    emit_report,
    is_handwritten_path,
    is_legacy_path,
    iter_rtl_sources,
    collect_placeholder_policy_findings,
    cmn_mem_bits,
    cmn_mem_is_large,
    cmn_mem_tag_of,
    discover_rtl,
    is_cmn_mem_module,
    is_placeholder_module,
    large_cmn_mem_lib_files,
    hooks_extra_for,
    parse_cmn_mem_tag,
    is_eqy_tie_low_port,
    read_cmn_mem_threshold_bits,
    looks_generated,
    parse_port_decls,
    print_tool_versions,
    rel,
    rtl_pyc_lib,
    run_cmd,
    shutil_which,
    yosys_inc_prefix,
)

# --- architecture-owned knobs (confirm with Xia / design before editing) ---
EMIT_SCRIPT = "scripts/emit_rtl.py"
EMIT_CMD = [sys.executable, EMIT_SCRIPT]
# --------------------------------------------------------------------------

def write_hooks_wrapper(hooks_path: Path, module: str, dest: Path) -> list[str]:
    """HOOKS with tb_test_mode / extra inputs tied low (SPEC §11).

    Tie-low ports are deleted and their uses become 1'b0 so the gate top
    matches PRODUCT (no wrapper hierarchy). Observe (tb_obs_*) stay open
    via a thin wrapper only when present.
    """
    ports = parse_port_decls(hooks_path)
    tied: list[str] = []
    observe: list[str] = []
    for _kind, name, _packed in ports:
        if is_eqy_tie_low_port(name):
            tied.append(name)
        elif name.startswith("tb_obs_"):
            observe.append(name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = hooks_path.read_text(encoding="utf-8")
    for name in tied:
        text = re.sub(
            rf"^[ \t]*input(?:[ \t]+\[[^\]]+\])?[ \t]+{re.escape(name)},?[ \t]*\n",
            "",
            text,
            flags=re.M,
        )
        text = re.sub(rf"\b{re.escape(name)}\b", "1'b0", text)
    if not observe:
        dest.write_text(text, encoding="utf-8")
        return tied
    tmp = dest.with_name(dest.stem + "_tied.v")
    tmp.write_text(text, encoding="utf-8")
    exposed = [
        (kind, name, packed)
        for kind, name, packed in ports
        if name not in tied and name not in observe
    ]
    lines = [
        f"// Auto-generated eqy wrapper: {module} hooks with extras tied low.",
        f"module {module}_eqy_hooks (",
    ]
    if exposed:
        lines.append("  " + ",\n  ".join(n for _k, n, _p in exposed))
    lines.append(");")
    for kind, name, packed in exposed:
        width = f" {packed}" if packed else ""
        lines.append(f"  {kind}{width} {name};")
    conns = [f".{n}({n})" for _k, n, _p in exposed]
    for name in observe:
        conns.append(f".{name}()")
    lines.append(f"  {module} u_hooks (")
    lines.append("    " + ",\n    ".join(conns))
    lines.append("  );")
    lines.append("endmodule")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tied + observe


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


def _yosys_inc() -> str:
    """-I rtl/pyc_lib when present (SPEC §2.2 `include pyc_reg.v)."""
    lib = rtl_pyc_lib()
    return yosys_inc_prefix([lib]) if lib else ""


def _yosys_equiv_script(
    product: Path,
    gold_top: str,
    gate_reads: list[str],
    gate_top: str,
    lib_files: list[Path] | None = None,
) -> str:
    """Yosys equiv_make / equiv_simple / equiv_induct / equiv_status -assert."""
    libs = _lib_reads(lib_files)
    inc = _yosys_inc()
    gold_read = f"read_verilog -sv {inc} {product}".replace("  ", " ")
    return "\n".join(
        [
            gold_read,
            *libs,
            f"hierarchy -check -top {gold_top}",
            "proc",
            "flatten",
            "opt",
            "design -save gold",
            "design -reset",
            *gate_reads,
            *libs,
            f"hierarchy -check -top {gate_top}",
            "proc",
            "flatten",
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
    inc = _yosys_inc()
    if extra_ports is None:
        gate_top = module
        gate_reads = [f"read_verilog -sv {inc} {hooks}".replace("  ", " ")]
        kind = "no-hook leaf, ports 1:1"
    else:
        wrap = work / f"{module}_eqy_hooks.v"
        tied = write_hooks_wrapper(hooks, module, wrap)
        observe = [n for n in tied if n.startswith("tb_obs_")]
        if observe:
            gate_top = f"{module}_eqy_hooks"
            tied_src = wrap.with_name(wrap.stem + "_tied.v")
            gate_reads = [
                f"read_verilog -sv {inc} {tied_src}".replace("  ", " "),
                f"read_verilog -sv {inc} {wrap}".replace("  ", " "),
            ]
        else:
            gate_top = module
            gate_reads = [f"read_verilog -sv {inc} {wrap}".replace("  ", " ")]
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
        f"emit knobs: EMIT_SCRIPT={EMIT_SCRIPT} EMIT_CMD={' '.join(EMIT_CMD)} "
        f"equiv_only={args.equiv_only}"
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
    if not args.equiv_only:
        findings.extend(collect_placeholder_policy_findings("emit"))
    emit_path = REPO_ROOT / EMIT_SCRIPT
    if args.equiv_only:
        print("equiv-only: skip emit+diff")
    elif not emit_path.is_file():
        print(f"skip emit+diff: {EMIT_SCRIPT} does not exist (pyCircuit emit not on this branch)")
    else:
        print(f"=== {' '.join(EMIT_CMD)} ===")
        proc = run_cmd(EMIT_CMD)
        print(proc.stdout or "")
        if proc.returncode != 0:
            findings.append(
                Finding(
                    check="emit",
                    module="*",
                    file=EMIT_SCRIPT,
                    rule="EMIT_FAIL",
                    message=f"{EMIT_SCRIPT} exited {proc.returncode}",
                )
            )
            return emit_report("emit", findings)
        diff = run_cmd(["git", "diff", "--exit-code", "--", "rtl"])
        porcelain = run_cmd(["git", "status", "--porcelain", "--", "rtl"])
        extra = [
            line for line in (porcelain.stdout or "").splitlines() if line.startswith("?")
        ]
        if diff.returncode != 0 or extra:
            msg = "rtl/ drifted after emit (hand-edit or stale generated files)"
            if extra:
                msg += f"; untracked: {[ln[3:] for ln in extra]}"
            print(diff.stdout or "")
            findings.append(
                Finding(
                    check="emit",
                    module="*",
                    file="rtl/",
                    rule="EMIT_DIFF",
                    message=msg,
                )
            )

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
                f"({bits} bits > {thresh}); parents blackbox both sides"
            )
            findings.append(
                Finding(
                    check="emit",
                    module=module,
                    file=leaf["product"],
                    rule="CMN_MEM_LARGE",
                    message=(
                        f"large variant ({bits} bits > {thresh}); "
                        "full PRODUCT≡HOOKS skipped; parents -lib the same cell"
                    ),
                    bucket="report",
                )
            )
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
