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
    load_hooks_ports,
    looks_generated,
    parse_ports,
    print_tool_versions,
    rel,
    run_cmd,
    shutil_which,
)

# --- architecture-owned knobs (confirm with Xia / design before editing) ---
EMIT_SCRIPT = "scripts/emit_rtl.py"
EMIT_CMD = [sys.executable, EMIT_SCRIPT]
# --------------------------------------------------------------------------

def write_hooks_wrapper(hooks_path: Path, module: str, dest: Path) -> list[str]:
    """Wrap HOOKS so tb_test_mode=0 and tb_inj_* are tied low (SPEC §11)."""
    ports = parse_ports(hooks_path)
    tied: list[str] = []
    exposed: list[tuple[str, str]] = []
    for kind, name in ports:
        if name == "tb_test_mode" or name.startswith("tb_inj_"):
            tied.append(name)
        elif name.startswith("tb_obs_"):
            tied.append(name)  # observe-only; leave unconnected on the wrapper
        else:
            exposed.append((kind, name))
    lines = [
        f"// Auto-generated eqy wrapper: {module} hooks with tb_test_mode=0,",
        "// all tb_inj_* tied low. Do not commit.",
        f"module {module}_eqy_hooks (",
    ]
    if exposed:
        lines.append("  " + ",\n  ".join(n for _k, n in exposed))
    lines.append(");")
    for kind, name in exposed:
        lines.append(f"  {kind} {name};")
    conns = [f".{n}({n})" for _k, n in exposed]
    for name in tied:
        if name.startswith("tb_obs_"):
            conns.append(f".{name}()")
        else:
            conns.append(f".{name}(1'b0)")
    lines.append(f"  {module} u_hooks (")
    lines.append("    " + ",\n    ".join(conns))
    lines.append("  );")
    lines.append("endmodule")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tied


def _yosys_equiv_script(
    product: Path,
    gold_top: str,
    gate_reads: list[str],
    gate_top: str,
) -> str:
    """Yosys fallback used on design PR #12 when eqy is not on PATH.

    Commands: equiv_make / equiv_simple / equiv_induct / equiv_status -assert.
    """
    return "\n".join(
        [
            f"read_verilog -sv {product}",
            f"hierarchy -check -top {gold_top}",
            "proc",
            "opt",
            "design -save gold",
            "design -reset",
            *gate_reads,
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


def run_equiv(
    module: str,
    product: Path,
    hooks: Path,
    extra_ports: list[str] | None,
) -> Finding | None:
    """Prove PRODUCT≡HOOKS. Primary: eqy. Fallback: Yosys equiv_*."""
    work = OUT_DIR / "eqy" / module
    work.mkdir(parents=True, exist_ok=True)
    gold_top = module
    if extra_ports is None:
        gate_top = module
        gate_reads = [f"read_verilog -sv {hooks}"]
        kind = "no-hook leaf, ports 1:1"
    else:
        wrap = work / f"{module}_eqy_hooks.v"
        tied = write_hooks_wrapper(hooks, module, wrap)
        gate_top = f"{module}_eqy_hooks"
        gate_reads = [f"read_verilog -sv {hooks}", f"read_verilog -sv {wrap}"]
        kind = f"hooked; extra inputs tied low ({tied or 'none'})"

    eqy_bin = shutil_which("eqy")
    yosys_bin = shutil_which("yosys")
    if eqy_bin:
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
                    f"prep -top {gold_top}",
                    "",
                    "[gate]",
                    *gate_reads,
                    f"prep -top {gate_top}",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"--- EQUIV tool=eqy {module} ({kind}) ---")
        proc = run_cmd(["eqy", "-f", str(eqy_file)], cwd=work, timeout=180)
    elif yosys_bin:
        tool = "yosys-equiv"
        ys = work / f"{module}_equiv.ys"
        ys.write_text(
            _yosys_equiv_script(product, gold_top, gate_reads, gate_top) + "\n",
            encoding="utf-8",
        )
        print(
            f"--- EQUIV tool=yosys-equiv {module} ({kind}); "
            "eqy not on PATH, fallback equiv_make/equiv_simple/"
            "equiv_induct/equiv_status -assert ---"
        )
        proc = run_cmd(["yosys", "-s", str(ys)], cwd=work, timeout=180)
    else:
        print(f"--- EQUIV tool=NONE {module}: eqy and yosys both missing ---")
        return Finding(
            check="emit",
            module=module,
            file=rel(product),
            rule="EQUIV_TOOL_MISSING",
            message="eqy not on PATH and yosys not on PATH; cannot prove PRODUCT≡hooks",
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
    print_tool_versions(["python", "yosys", "eqy"])
    print(
        f"emit knobs: EMIT_SCRIPT={EMIT_SCRIPT} EMIT_CMD={' '.join(EMIT_CMD)}"
    )
    pyc_layers = discover_layers(REPO_ROOT / "pycircuit")
    rtl_layers = discover_layers(REPO_ROOT / "rtl")
    formal_layers = discover_layers(REPO_ROOT / "formal")
    print(
        f"discovered layers: pycircuit={pyc_layers or '[]'} "
        f"rtl={rtl_layers or '[]'} formal={formal_layers or '[]'}"
    )

    findings: list[Finding] = []
    emit_path = REPO_ROOT / EMIT_SCRIPT
    if not emit_path.is_file():
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
                    "gate/handwritten.yml (or the entry has no gatekeeper approver)"
                ),
            )
        )

    table = load_hooks_ports()
    for leaf in discover_leaf_pairs():
        product = REPO_ROOT / leaf["product"]
        hooks = REPO_ROOT / leaf["hooks"]
        module = leaf["module"]
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
        extra = table.get(module)
        hit = run_equiv(module, product, hooks, extra)
        if hit:
            findings.append(hit)

    return emit_report("emit", findings)


if __name__ == "__main__":
    raise SystemExit(main())
