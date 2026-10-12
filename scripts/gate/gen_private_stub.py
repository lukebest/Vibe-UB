#!/usr/bin/env python3
"""Generate a pyCircuit port-only stub and emit rtl/<layer>/stub/<leaf>.v via pycc.

Does not splice Verilog by hand (D5). Both .py and .v carry:

    // contract_sha256: <hex>
    // generated-by: scripts/gate/gen_private_stub.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contract_hash import contract_sha256
from gatelib import REPO_ROOT, run_cmd
from private_leaves import (
    GENERATED_BY,
    discover_contract_files,
    parse_contract_file,
    stub_py_path,
    stub_rtl_path,
)


def _width_expr(width: object) -> str:
    if isinstance(width, int):
        return str(width)
    text = str(width)
    if text.lower() == "unknown":
        return "1"
    if text.isidentifier():
        return f"int({text})" if False else "1"
    try:
        return str(int(text))
    except ValueError:
        return "1"


def render_py(data: dict, digest: str) -> str:
    leaf = str(data["leaf"])
    ports = data.get("ports") if isinstance(data.get("ports"), list) else []
    clock = data.get("clock") if isinstance(data.get("clock"), dict) else {}
    clk_name = str(clock.get("name") or "core_clk")
    rst_name = str(clock.get("reset") or "rst_pyc")
    lines = [
        f"# contract_sha256: {digest}",
        f"# generated-by: {GENERATED_BY}",
        f'"""Public port-only stub for {leaf}. Bit layout is private (S-01(b))."""',
        "",
        "from __future__ import annotations",
        "",
        "from pycircuit import Circuit, module, u",
        "",
        "",
        f'@module(name="{leaf}")',
        "def build(m: Circuit) -> None:",
        f"    clk = m.clock({clk_name!r})",
        f"    rst = m.reset({rst_name!r})",
        "    _ = (clk, rst)",
    ]
    seen = {clk_name, rst_name}
    for port in ports:
        if not isinstance(port, dict):
            continue
        name = port.get("name")
        if not name or name in seen:
            continue
        seen.add(str(name))
        width = _width_expr(port.get("width"))
        direction = port.get("dir")
        if direction == "in":
            lines.append(f"    m.input({name!r}, width={width})")
        else:
            lines.append(f"    m.output({name!r}, u({width}, 0))")
    lines.append("")
    lines.append(f"build.__pycircuit_name__ = {leaf!r}")
    lines.append("")
    return "\n".join(lines)


def header_lines(digest: str) -> str:
    return f"// contract_sha256: {digest}\n// generated-by: {GENERATED_BY}\n"


def _find_pycc() -> str | None:
    found = shutil.which("pycc")
    if found:
        return found
    for cand in (
        REPO_ROOT / ".pycircuit-venv" / "bin" / "pycc",
        REPO_ROOT / ".pycircuit_out" / "toolchain" / "install" / "bin" / "pycc",
    ):
        if cand.is_file():
            return str(cand)
    return None


def emit_verilog(py_path: Path, v_path: Path, digest: str) -> None:
    pycc = _find_pycc()
    v_path.parent.mkdir(parents=True, exist_ok=True)
    if pycc is None:
        raise SystemExit(
            "ERROR: pycc is not on PATH; cannot emit "
            f"{v_path} (D5: do not splice Verilog). "
            "Install via scripts/gate/setup_pycircuit.sh"
        )
    proc = run_cmd(
        [pycc, "--emit=verilog", "--logic-depth=64", str(py_path)],
        cwd=py_path.parent,
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"ERROR: pycc failed for {py_path}: {proc.stdout}{proc.stderr}"
        )
    produced = None
    for cand in py_path.parent.glob("*.v"):
        produced = cand
        break
    if produced is None:
        raise SystemExit(f"ERROR: pycc wrote no .v next to {py_path}")
    body = produced.read_text(encoding="utf-8")
    if "contract_sha256:" not in body.splitlines()[0] if body else True:
        body = header_lines(digest) + body
    v_path.write_text(body, encoding="utf-8")
    if produced.resolve() != v_path.resolve():
        produced.unlink(missing_ok=True)


def generate_one(path: Path, root: Path) -> Path:
    data, errs = parse_contract_file(path, root)
    if data is None or errs:
        msg = "; ".join(e.message for e in errs) if errs else "parse failed"
        raise SystemExit(f"ERROR: {path}: {msg}")
    digest = contract_sha256(path)
    layer = str(data["_layer"])
    leaf = str(data["leaf"])
    py_path = stub_py_path(root, layer, leaf)
    py_path.parent.mkdir(parents=True, exist_ok=True)
    py_path.write_text(render_py(data, digest), encoding="utf-8")
    v_path = stub_rtl_path(root, layer, leaf)
    emit_verilog(py_path, v_path, digest)
    print(f"wrote {py_path.relative_to(root)} and {v_path.relative_to(root)}")
    return v_path


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = REPO_ROOT
    if args == ["--all"] or not args:
        files = discover_contract_files(root)
        if not files:
            print("gen_private_stub: no docs/arch/*/contracts/*.md")
            return 0
        for path in files:
            generate_one(path, root)
        return 0
    for raw in args:
        generate_one(Path(raw), root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
