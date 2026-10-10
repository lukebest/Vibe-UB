#!/usr/bin/env python3
"""PRODUCT vs HOOKS formal check per generated leaf (SPEC §11 (d)).

Uses ``eqy`` when present. Otherwise Yosys
``equiv_make`` / ``equiv_simple`` / ``equiv_induct`` / ``equiv_status -assert``.

This batch has no SPEC §10 hooks: HOOKS ports == PRODUCT ports
(Xia: do **not** add unused ``tb_test_mode``). Compare identical ports.

If a later registered leaf adds §10 ``tb_*`` inputs, those are tied
(``tb_test_mode=0``, ``tb_inj_*=0``) before compare.
``ub_rst_sync.sv`` is whitelist SV and is not compared.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VENV_PY = Path(__import__("os").environ.get("UB_PYC_VENV", "/tmp/venv")) / "bin" / "python"


def _reexec_venv() -> None:
    import os

    if not VENV_PY.is_file():
        return
    if Path(sys.executable).resolve() == VENV_PY.resolve():
        return
    os.execv(str(VENV_PY), [str(VENV_PY), *sys.argv])


_reexec_venv()

PYC = REPO / "pycircuit"
if str(PYC) not in sys.path:
    sys.path.insert(0, str(PYC))

from emit import emit_all, register_batch1  # noqa: E402
from lib.elab_open import yosys_chparam_cmd  # noqa: E402
from lib.registry import registered  # noqa: E402

PORT_RE = re.compile(
    r"\b(input|output|inout)\s+wire\s+(?:\[[^\]]+\]\s+)?(\w+)",
)


def _ports(text: str) -> list[tuple[str, str]]:
    block = text.split("module", 1)[1].split(");", 1)[0]
    return [(d, n) for d, n in PORT_RE.findall(block)]


def _inputs(text: str) -> list[str]:
    return [n for d, n in _ports(text) if d == "input"]


def _chparam(name: str) -> str:
    if name in ("ub_pcs_scrambler", "ub_pcs_descrambler"):
        return yosys_chparam_cmd() + "; "
    return ""


def _write_tied_wrapper(
    dest: Path,
    *,
    name: str,
    product_text: str,
    hooks_text: str,
    extra_inputs: list[str],
) -> Path:
    """Instantiate HOOKS with tb_test_mode=0 and tb_inj_* tied low."""
    prod_ports = _ports(product_text)
    hooks_ports = _ports(hooks_text)
    extra = set(extra_inputs)
    lines = [
        f"// Auto wrapper: HOOKS {name} with hook inputs tied (SPEC §11 (d)).",
        f"module {name}_hooks_tied (",
    ]
    decls = []
    for direction, pname in prod_ports:
        # recover width from hooks text
        m = re.search(
            rf"{direction}\s+wire\s+(\[[^\]]+\]\s+)?{pname}\b",
            hooks_text,
        )
        width = (m.group(1) or "").strip()
        space = " " if width else ""
        decls.append(f"  {direction} wire {width}{space}{pname}")
    lines.append(",\n".join(decls))
    lines.append(");")
    lines.append(f"  {name} u_hooks (")
    conns = [f"    .{pname}({pname})" for _, pname in prod_ports]
    for direction, pname in hooks_ports:
        if pname not in extra:
            continue
        if direction != "input":
            conns.append(f"    .{pname}()")
            continue
        if pname == "tb_test_mode":
            conns.append("    .tb_test_mode(1'b0)")
        else:
            conns.append(f"    .{pname}('0)")
    lines.append(",\n".join(conns))
    lines.append("  );")
    lines.append("endmodule")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def _incdir() -> str:
    return f"-I{REPO / 'rtl' / 'pyc_lib'} "


def _extra_v(name: str) -> str:
    if name.startswith("ub_dll_bcrc"):
        return _incdir() + " "
    return ""


def _yosys_script(
    *,
    gold: Path,
    gate: Path,
    gold_top: str,
    gate_top: str,
    ch: str,
) -> str:
    extra = _extra_v(gold_top)
    return f"""
read_verilog -sv {extra}{gold}
{ch}hierarchy -check -top {gold_top}
proc; flatten; opt
rename {gold_top} gold
design -stash gold

read_verilog -sv {extra}{gate}
{ch}hierarchy -check -top {gate_top}
proc; flatten; opt
rename {gate_top} gate
design -stash gate

design -reset
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
equiv_simple equiv
equiv_induct equiv
equiv_status -assert equiv
"""


def _run_yosys(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["yosys", "-q", "-p", script],
        text=True,
        capture_output=True,
        check=False,
    )


def _run_eqy(gold: Path, gate: Path, top: str, work: Path) -> subprocess.CompletedProcess[str] | None:
    eqy = shutil.which("eqy")
    if eqy is None:
        return None
    cfg = work / f"{top}.eqy"
    cfg.write_text(
        f"[gold]\nread_verilog -sv {gold}\nprep -top {top}\n\n"
        f"[gate]\nread_verilog -sv {gate}\nprep -top {top}\n\n"
        f"[strategy simple]\nuse sat\n\n",
        encoding="utf-8",
    )
    return subprocess.run(
        [eqy, "-f", str(cfg)],
        text=True,
        capture_output=True,
        check=False,
        cwd=work,
    )


def check_leaf(leaf, rtl: Path, work: Path) -> tuple[bool, str]:
    product = rtl / leaf.layer / f"{leaf.name}.v"
    hooks = rtl / leaf.layer / "hooks" / f"{leaf.name}.v"
    ptxt = product.read_text(encoding="utf-8")
    htxt = hooks.read_text(encoding="utf-8")
    extra = [n for n in _inputs(htxt) if n not in set(_inputs(ptxt))]
    gate = hooks
    gate_top = leaf.name
    if extra:
        gate = work / f"{leaf.name}_hooks_tied.v"
        # wrapper needs the HOOKS module
        (work / f"{leaf.name}_hooks.v").write_text(htxt, encoding="utf-8")
        _write_tied_wrapper(
            gate,
            name=leaf.name,
            product_text=ptxt,
            hooks_text=htxt,
            extra_inputs=extra,
        )
        # concatenate hooks + wrapper for one read
        combo = work / f"{leaf.name}_gate.v"
        combo.write_text(
            (work / f"{leaf.name}_hooks.v").read_text(encoding="utf-8")
            + "\n"
            + gate.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        gate = combo
        gate_top = f"{leaf.name}_hooks_tied"

    ch = _chparam(leaf.name)
    eqy_run = _run_eqy(product, gate if extra else hooks, leaf.name, work)
    if eqy_run is not None:
        ok = eqy_run.returncode == 0
        how = "eqy"
        detail = (eqy_run.stdout + eqy_run.stderr).strip()
        return ok, f"{how} {'OK' if ok else 'FAIL'}\n{detail}"

    script = _yosys_script(
        gold=product,
        gate=gate,
        gold_top=leaf.name,
        gate_top=gate_top,
        ch=ch,
    )
    run = _run_yosys(script)
    ok = run.returncode == 0
    detail = (run.stdout + run.stderr).strip()
    return ok, f"yosys equiv_make/simple/induct {'OK' if ok else 'FAIL'}\n{detail}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-emit", action="store_true")
    args = parser.parse_args()
    if not args.no_emit:
        emit_all()
    register_batch1()
    rtl = REPO / "rtl"
    err = 0
    with tempfile.TemporaryDirectory(prefix="ub-equiv-") as td:
        work = Path(td)
        for leaf in registered():
            print(f"==== PRODUCT vs HOOKS {leaf.layer}/{leaf.name} ====")
            ok, msg = check_leaf(leaf, rtl, work)
            print(msg if msg.strip() else ("OK" if ok else "FAIL"))
            if not ok:
                err = 1
    return err


if __name__ == "__main__":
    raise SystemExit(main())
