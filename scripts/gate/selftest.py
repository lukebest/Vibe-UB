#!/usr/bin/env python3
"""Deliberate-fail fixtures: each new gate check must catch a planted violation."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from formal_bind import check_formal_binds
from gatelib import (
    Finding,
    collect_lock_completeness_findings,
    discover_pycircuit_leaves,
    discover_pycircuit_lib_helpers,
    hooks_extra_for,
    import_root_shadow_findings,
    leaf_process_env,
    leaf_python_argv,
    mark_deleted_findings,
    parse_port_decls,
    repo_root_on_sys_path,
    run_cmd,
    sha256_file,
)
from hooks_port_consistency import compare_ports
from large_mem_manifest import check_large_mem_manifest
from pyc_lib_check import check_pyc_lib
from pycircuit_provenance import static_splice_check
from rtl_emit_consistency import (
    compare_emitted_rtl,
    emit_unavailable_findings,
    run_equiv,
)


def _fail(name: str, detail: str) -> None:
    print(f"SELFTEST FAIL {name}: {detail}")
    raise SystemExit(1)


def _expect_rule(name: str, findings: list[Finding], rule: str) -> Finding:
    hits = [f for f in findings if f.rule == rule]
    if not hits:
        got = sorted({f.rule for f in findings}) or ["(none)"]
        _fail(name, f"expected rule {rule}, got {got}")
    print(f"SELFTEST PASS {name}: {rule} ({hits[0].message[:80]})")
    return hits[0]


def _v(path: Path, module: str, ports: str, body: str = "") -> None:
    """Write a tiny netlist. `ports` is a comma-separated `dir name` list."""
    path.parent.mkdir(parents=True, exist_ok=True)
    decls: list[str] = []
    names: list[str] = []
    for chunk in ports.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split()
        if len(parts) >= 2:
            decls.append(f"  {parts[0]} {parts[1]};")
            names.append(parts[1])
        else:
            decls.append(f"  input {parts[0]};")
            names.append(parts[0])
    header = ", ".join(names)
    extra = f"{body}\n" if body else ""
    path.write_text(
        f"module {module} ({header});\n" + "\n".join(decls) + f"\n{extra}endmodule\n",
        encoding="utf-8",
    )


def test_emit_skip_missing_script() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        missing = Path(tmp) / "scripts" / "emit_rtl.py"
        hits = emit_unavailable_findings(missing)
        f = _expect_rule("emit-skip-missing-script", hits, "EMIT_SKIP")
        if f.bucket != "report":
            _fail("emit-skip-missing-script", "skip must be report-only")


def test_emit_skip_pycc() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        present = Path(tmp) / "emit_rtl.py"
        present.write_text("# dummy\n", encoding="utf-8")
        hits = emit_unavailable_findings(
            present, pycc_ready=False, reason="BLOCKER: apt install failed"
        )
        f = _expect_rule("emit-skip-pycc", hits, "EMIT_SKIP")
        if "apt install failed" not in f.message and "BLOCKER" not in f.message:
            _fail("emit-skip-pycc", "reason not in message")
        if f.bucket != "report":
            _fail("emit-skip-pycc", "skip must be report-only")


def test_emit_byte_diff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        gen = root / "gen" / "pcs"
        com = root / "com" / "pcs"
        _v(gen / "foo.v", "foo", "input clk")
        _v(com / "foo.v", "foo", "input clk, input rst")
        hits = compare_emitted_rtl(root / "gen", root / "com")
        _expect_rule("emit-byte-diff", hits, "EMIT_DIFF")


def test_lock_incomplete() -> None:
    hits = collect_lock_completeness_findings(
        "emit", lock={"llvm_lock": "19.1.1", "mlir_lock": "19.1.1"}
    )
    _expect_rule("lock-incomplete", hits, "TOOLCHAIN_LOCK_INCOMPLETE")


def test_large_v_committed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        rtl = Path(tmp) / "rtl"
        _v(
            rtl / "cmn" / "ub_cmn_mem_1r1w_d512w64.v",
            "ub_cmn_mem_1r1w_d512w64",
            "input core_clk",
        )
        hits = check_large_mem_manifest(
            rtl,
            generated_rtl=None,
            emit_available=False,
            pycc_ready=False,
            skip_reason="selftest",
            thresh=4096,
        )
        _expect_rule("large-v-committed", hits, "LARGE_V_COMMITTED")


def test_manifest_wrong_sha() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        rtl = root / "rtl"
        gen = root / "gen"
        name = "ub_cmn_mem_1r1w_d512w64"
        man = rtl / "cmn" / "manifest.yml"
        man.parent.mkdir(parents=True)
        prod = gen / "cmn" / f"{name}.v"
        hooks = gen / "cmn" / "hooks" / f"{name}.v"
        _v(prod, name, "input core_clk")
        _v(hooks, name + "_hooks", "input core_clk")
        # rewrite hooks with same module body except name for byte-except-name
        hooks.write_text(prod.read_text(encoding="utf-8").replace(name, name), encoding="utf-8")
        hooks.write_text(
            prod.read_text(encoding="utf-8").replace(
                f"module {name}", f"module {name}"
            ),
            encoding="utf-8",
        )
        # Make hooks differ only by module name so BODY check passes.
        hooks.write_text(
            prod.read_text(encoding="utf-8").replace(
                f"module {name} ", f"module {name}_h "
            ),
            encoding="utf-8",
        )
        man.write_text(
            "\n".join(
                [
                    "variants:",
                    f"  - name: {name}",
                    "    params:",
                    "      DEPTH: 512",
                    "      WIDTH: 64",
                    "    pycc: pyc4.0",
                    "    product_sha256: deadbeef" + "0" * 56,
                    f"    hooks_sha256: {sha256_file(hooks)}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        hits = check_large_mem_manifest(
            rtl,
            generated_rtl=gen,
            emit_available=True,
            pycc_ready=True,
            thresh=4096,
        )
        _expect_rule("manifest-wrong-sha", hits, "MANIFEST_SHA")


def test_manifest_unproducible() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        rtl = Path(tmp) / "rtl"
        gen = Path(tmp) / "gen"
        gen.mkdir()
        man = rtl / "cmn" / "manifest.yml"
        man.parent.mkdir(parents=True)
        man.write_text(
            "\n".join(
                [
                    "variants:",
                    "  - name: ub_cmn_mem_1r1w_d1024w64",
                    "    params: {DEPTH: 1024, WIDTH: 64}",
                    "    pycc: pyc4.0",
                    "    product_sha256: " + "ab" * 32,
                    "    hooks_sha256: " + "cd" * 32,
                    "",
                ]
            ),
            encoding="utf-8",
        )
        hits = check_large_mem_manifest(
            rtl,
            generated_rtl=gen,
            emit_available=True,
            pycc_ready=True,
            thresh=4096,
        )
        _expect_rule("manifest-unproducible", hits, "MANIFEST_UNPRODUCIBLE")


def test_stray_pyc_reg() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        rtl = Path(tmp) / "rtl"
        _v(rtl / "pcs" / "pyc_reg.v", "pyc_reg", "input clk")
        hits = check_pyc_lib(rtl, lock_src=None)
        _expect_rule("stray-pyc-reg", hits, "PYC_PRIMITIVE_STRAY")


def test_pyc_lib_skip_missing_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        rtl = Path(tmp) / "rtl"
        rtl.mkdir()
        hits = check_pyc_lib(rtl, lock_src=None)
        f = _expect_rule("pyc-lib-skip-missing", hits, "PYC_LIB_SKIP")
        if f.bucket != "report":
            _fail("pyc-lib-skip-missing", "missing rtl/pyc_lib must not fail")
        if any(h.bucket == "new" for h in hits):
            _fail("pyc-lib-skip-missing", "must not introduce blocking findings")


def test_pyc_lib_byte_diff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        rtl = Path(tmp) / "rtl"
        src = Path(tmp) / "pyCircuit"
        _v(rtl / "pyc_lib" / "pyc_reg.v", "pyc_reg", "input clk, input d")
        _v(src / "lib" / "pyc_reg.v", "pyc_reg", "input clk")
        hits = check_pyc_lib(rtl, lock_src=src)
        _expect_rule("pyc-lib-byte-diff", hits, "PYC_LIB_DIFF")


def test_unlisted_tb_obs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        prod = Path(tmp) / "prod.v"
        hooks = Path(tmp) / "hooks.v"
        _v(prod, "ub_foo", "input clk")
        _v(hooks, "ub_foo", "input clk, output tb_foo_obs_hit")
        hits = compare_ports("ub_foo", prod, hooks, None)
        _expect_rule("unlisted-tb-obs", hits, "HOOKS_PORT_UNEXPECTED")


def test_obs_must_be_output() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        prod = Path(tmp) / "prod.v"
        hooks = Path(tmp) / "hooks.v"
        extra = ["tb_test_mode", "tb_mem_tlb_obs_hit"]
        _v(prod, "ub_mem_tlb", "input clk")
        _v(
            hooks,
            "ub_mem_tlb",
            "input clk, input tb_test_mode, input tb_mem_tlb_obs_hit",
        )
        hits = compare_ports("ub_mem_tlb", prod, hooks, extra)
        _expect_rule("obs-must-be-output", hits, "HOOKS_PORT_DIR")


def test_sby_bind_missing_signal() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        net = repo / "rtl" / "cmn" / "ub_toy.v"
        sby = repo / "formal" / "cmn" / "toy.sby"
        ass = repo / "formal" / "cmn" / "toy_assert.sv"
        _v(net, "ub_toy", "input core_clk")
        sby.parent.mkdir(parents=True)
        sby.write_text(
            "\n".join(
                [
                    "[options]",
                    "mode bmc",
                    "[script]",
                    "read -sv rtl/cmn/ub_toy.v",
                    "read -sv formal/cmn/toy_assert.sv",
                    "prep -top ub_toy",
                    "[files]",
                    "rtl/cmn/ub_toy.v",
                    "formal/cmn/toy_assert.sv",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        ass.write_text(
            "\n".join(
                [
                    "module toy_assert(input core_clk, input ghost_sig);",
                    "endmodule",
                    "bind ub_toy toy_assert u_a (",
                    "  .core_clk(core_clk),",
                    "  .ghost_sig(ghost_sig)",
                    ");",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        hits = check_formal_binds(repo)
        _expect_rule("sby-bind-missing-signal", hits, "BIND_SIGNAL_MISSING")


def test_deleted_roster_not_error() -> None:
    # pycircuit/ is empty on current main; migrate roster paths are gone.
    planted = Finding(
        check="provenance",
        module="ub_dll_bcrc",
        file="pycircuit/dll/ub_dll_bcrc.py",
        rule="NO_PYCIRCUIT_IMPORT",
        message="leaf missing",
    )
    keep, deleted = mark_deleted_findings([planted])
    if keep:
        _fail("deleted-roster", f"missing roster file must leave keep empty, got {keep}")
    if not deleted or "已删除" not in deleted[0].message:
        _fail("deleted-roster", "expected 已删除 marker")
    print("SELFTEST PASS deleted-roster: 已删除 excluded from totals")


def _write_fake_layer(root: Path, *, helper_at_root: bool = False) -> Path:
    """Fake pycircuit/<layer> with lib/ helper and a leaf that imports it."""
    layer = root / "pycircuit" / "toy"
    lib = layer / "lib"
    lib.mkdir(parents=True)
    (layer / "__init__.py").write_text("", encoding="utf-8")
    (lib / "__init__.py").write_text("# helpers only\n", encoding="utf-8")
    (lib / "helper.py").write_text(
        "def mark():\n    return 'helper-ok'\n",
        encoding="utf-8",
    )
    (layer / "ub_toy.py").write_text(
        "from pycircuit import Circuit\n"
        "from toy.lib import helper\n"
        "FLAG = helper.mark()\n",
        encoding="utf-8",
    )
    (root / "pycircuit" / "__init__.py").write_text("", encoding="utf-8")
    if helper_at_root:
        (layer / "at_root_helper.py").write_text(
            "from pycircuit import Circuit\nROOT_HELPER = True\n",
            encoding="utf-8",
        )
    return layer


def test_layer_lib_discovered_and_emit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_fake_layer(root)
        leaves = discover_pycircuit_leaves(root / "pycircuit")
        names = {leaf["leaf"] for leaf in leaves}
        if "ub_toy" not in names:
            _fail("layer-lib-discover", f"leaf ub_toy not found: {names}")
        if "helper" in names or "lib" in names:
            _fail("layer-lib-discover", f"lib/ helper must not be a leaf: {names}")
        helpers = discover_pycircuit_lib_helpers(root / "pycircuit")
        if not any(p.name == "helper.py" for p in helpers):
            _fail("layer-lib-discover", f"lib helper not scanned: {helpers}")
        emit = root / "scripts" / "emit_rtl.py"
        emit.parent.mkdir(parents=True)
        emit.write_text(
            "from toy.lib import helper\nprint(helper.mark())\n",
            encoding="utf-8",
        )
        proc = run_cmd(
            leaf_python_argv(emit),
            cwd=root,
            env=leaf_process_env(root),
            timeout=30,
        )
        if proc.returncode != 0 or "helper-ok" not in (proc.stdout or ""):
            _fail(
                "layer-lib-emit",
                f"emit with PYTHONPATH=<repo>/pycircuit failed: {proc.stdout!r}",
            )
        print("SELFTEST PASS layer-lib-discover+emit: from toy.lib works; lib/ not a leaf")


def test_helper_at_layer_root_is_leaf() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_fake_layer(root, helper_at_root=True)
        names = {leaf["leaf"] for leaf in discover_pycircuit_leaves(root / "pycircuit")}
        if "at_root_helper" not in names:
            _fail(
                "helper-at-layer-root",
                f"file at pycircuit/<layer>/*.py must be a leaf: {names}",
            )
        if "helper" in names:
            _fail("helper-at-layer-root", "lib/helper.py must still be skipped")
        print("SELFTEST PASS helper-at-layer-root: layer-root .py is a leaf")


def test_repo_root_on_path_shadows() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_fake_layer(root)
        if not repo_root_on_sys_path([str(root)], root):
            _fail("import-root-shadow", "repo root on sys.path must be detected")
        if repo_root_on_sys_path([str(root / "pycircuit")], root):
            _fail(
                "import-root-shadow",
                "<repo>/pycircuit on PYTHONPATH is the import root, not a shadow",
            )
        hits = import_root_shadow_findings([str(root)], "provenance", root)
        _expect_rule("import-root-shadow", hits, "IMPORT_ROOT_SHADOW")
        # Reproduce #27: cwd/repo root on path → import pycircuit binds to the tree.
        bad_env = {
            **leaf_process_env(root),
            "PYTHONPATH": str(root),
            "PYTHONSAFEPATH": "0",
        }
        probe = (
            "import sys, pathlib\n"
            "print('path0=' + sys.path[0])\n"
            "try:\n"
            "    import pycircuit, inspect\n"
            "    loc = pathlib.Path(inspect.getfile(pycircuit)).resolve()\n"
            "    print('loc=' + str(loc))\n"
            "    tree = pathlib.Path(" + repr(str(root / 'pycircuit')) + ").resolve()\n"
            "    print('SHADOW_TREE' if loc == tree or loc.parent == tree else 'OTHER')\n"
            "except Exception as exc:\n"
            "    print('IMPORT_FAIL ' + type(exc).__name__ + ': ' + str(exc))\n"
        )
        proc = run_cmd(
            [sys.executable, "-c", probe],
            cwd=root,
            env=bad_env,
            timeout=30,
        )
        text = proc.stdout or ""
        if "SHADOW_TREE" not in text and "IMPORT_FAIL" not in text:
            _fail("import-root-shadow-repro", f"expected tree shadow or fail, got {text!r}")
        # Without <repo>/pycircuit on PYTHONPATH, from <layer>.lib fails (#27 mem).
        empty = {**leaf_process_env(root), "PYTHONPATH": ""}
        miss = run_cmd(
            [sys.executable, "-P", "-c", "from toy.lib import helper"],
            cwd=root,
            env=empty,
            timeout=30,
        )
        if miss.returncode == 0:
            _fail("import-root-shadow-repro", "from toy.lib must fail without import root")
        print(
            "SELFTEST PASS import-root-shadow: repo root shadows install; "
            "missing import root → No module named layer"
        )


def test_lib_helper_splice() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        helper = Path(tmp) / "bad.py"
        helper.write_text('VERILOG = "module sneak(); endmodule"\n', encoding="utf-8")
        hits = static_splice_check(helper, "bad")
        _expect_rule("lib-helper-splice", hits, "VERILOG_SPLICE")


def _write_ansi_csr_shape(path: Path, *, extra: str = "", addr_w: str = "[15:0]") -> None:
    """pycc-style ANSI list (one port per line). Old regex ate the next `input`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    extra_decl = f",\n  {extra}" if extra else ""
    path.write_text(
        "module ub_csr_toy (\n"
        "  input core_clk,\n"
        f"  input {addr_w} csr_addr,\n"
        "  output port_rst_pulse,\n"
        "  output csr_irq_en,\n"
        "  output [31:0] csr_port_cna"
        + extra_decl
        + "\n);\nendmodule\n",
        encoding="utf-8",
    )


def test_yosys_ansi_ports() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        prod = Path(tmp) / "prod.v"
        _write_ansi_csr_shape(prod)
        ports = parse_port_decls(prod, module="ub_csr_toy")
        names = [n for _k, n, _p in ports]
        if any(n in {"input", "output", "inout"} for n in names):
            _fail("yosys-ansi-ports", f"direction token eaten as name: {names}")
        for need in ("port_rst_pulse", "csr_irq_en", "csr_port_cna", "csr_addr"):
            if need not in names:
                _fail("yosys-ansi-ports", f"missing {need}: {names}")
        addr = next(t for t in ports if t[1] == "csr_addr")
        if addr[2] != "[15:0]":
            _fail("yosys-ansi-ports", f"csr_addr packed {addr}")
        print("SELFTEST PASS yosys-ansi-ports: Yosys port table keeps names+widths")


def test_hooks_missing_port() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        prod = Path(tmp) / "prod.v"
        hooks = Path(tmp) / "hooks.v"
        _write_ansi_csr_shape(prod)
        hooks.write_text(
            "module ub_csr_toy (\n"
            "  input core_clk,\n"
            "  input [15:0] csr_addr,\n"
            "  output port_rst_pulse,\n"
            "  output csr_irq_en\n"
            ");\nendmodule\n",
            encoding="utf-8",
        )
        hits = compare_ports("ub_csr_toy", prod, hooks, None)
        _expect_rule("hooks-missing-port", hits, "HOOKS_PORT_MISMATCH")


def test_hooks_wrong_width() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        prod = Path(tmp) / "prod.v"
        hooks = Path(tmp) / "hooks.v"
        _write_ansi_csr_shape(prod)
        _write_ansi_csr_shape(hooks, addr_w="[7:0]")
        hits = compare_ports("ub_csr_toy", prod, hooks, None)
        _expect_rule("hooks-wrong-width", hits, "HOOKS_PORT_WIDTH")


def _wide_combo(path: Path, module: str, width: int, flip_bit: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    expr = f"data_in"
    if flip_bit is not None:
        expr = f"{{data_in[{width - 1}:{flip_bit + 1}], ~data_in[{flip_bit}], data_in[{flip_bit - 1}:0]}}" if flip_bit else f"{{data_in[{width - 1}:1], ~data_in[0]}}"
    path.write_text(
        f"module {module} (\n"
        f"  input [{width - 1}:0] data_in,\n"
        f"  output [{width - 1}:0] data_out\n"
        ");\n"
        f"  assign data_out = {expr};\n"
        "endmodule\n",
        encoding="utf-8",
    )


def _write_lane_dist_x8(path: Path, flip_bit: int | None = None) -> None:
    """8-lane 256-bit splitter (SPEC x8 / PMA_W=32). No hook ports."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lanes = ", ".join(f"lane{i}" for i in range(8))
    if flip_bit == 0:
        assigns = (
            "  wire [255:0] src;\n"
            "  assign src = {data_in[255:1], ~data_in[0]};\n"
            + "\n".join(
                f"  assign lane{i} = src[{i * 32 + 31}:{i * 32}];" for i in range(8)
            )
        )
    else:
        assigns = "\n".join(
            f"  assign lane{i} = data_in[{i * 32 + 31}:{i * 32}];" for i in range(8)
        )
    path.write_text(
        "module ub_pcs_lane_dist_x8 (\n"
        "  input [255:0] data_in,\n"
        f"  output [31:0] {lanes}\n"
        ");\n"
        f"{assigns}\n"
        "endmodule\n",
        encoding="utf-8",
    )


def test_equiv_wide_bus_and_flip() -> None:
    """160-bit (BCRC-style) and 256-bit (lane_dist_x8-style) through the wrapper."""
    cases = [
        ("ub_dll_bcrc_bus", 160),
        ("ub_pcs_lane_dist_x8_bus", 256),
    ]
    for module, width in cases:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prod = root / f"{module}.v"
            hooks = root / "hooks.v"
            fake = root / "fake.v"
            _wide_combo(prod, module, width)
            _wide_combo(hooks, module, width)
            _wide_combo(fake, module, width, flip_bit=0)
            hit = run_equiv(module, prod, hooks, None)
            if hit is not None:
                _fail(f"equiv-{module}", f"identical wide bus must prove: {hit.message}")
            print(f"SELFTEST PASS equiv-{module}: PRODUCT≡HOOKS via wrapper")
            bad = run_equiv(module, prod, fake, None)
            if bad is None:
                _fail(f"equiv-{module}-flip", "one flipped bus bit must fail")
            if bad.rule != "EQUIV_FAIL":
                _fail(f"equiv-{module}-flip", f"expected EQUIV_FAIL, got {bad.rule}")
            print(f"SELFTEST PASS equiv-{module}-flip: fake bit fail")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        prod = root / "ub_pcs_lane_dist_x8.v"
        hooks = root / "hooks.v"
        fake = root / "fake.v"
        _write_lane_dist_x8(prod)
        _write_lane_dist_x8(hooks)
        _write_lane_dist_x8(fake, flip_bit=0)
        ph = compare_ports("ub_pcs_lane_dist_x8", prod, hooks, None)
        if ph:
            _fail("ports-ub_pcs_lane_dist_x8", ph[0].message)
        print("SELFTEST PASS ports-ub_pcs_lane_dist_x8: Yosys PRODUCT/HOOKS")
        hit = run_equiv("ub_pcs_lane_dist_x8", prod, hooks, None)
        if hit is not None:
            _fail("equiv-ub_pcs_lane_dist_x8", f"x8 leaf must prove: {hit.message}")
        print("SELFTEST PASS equiv-ub_pcs_lane_dist_x8: 256-bit / 8-lane through wrapper")
        bad = run_equiv("ub_pcs_lane_dist_x8", prod, fake, None)
        if bad is None:
            _fail("equiv-ub_pcs_lane_dist_x8-flip", "one flipped bus bit must fail")
        print("SELFTEST PASS equiv-ub_pcs_lane_dist_x8-flip: fake bit fail")


def _ensure_git_rev(rev: str) -> None:
    probe = run_cmd(["git", "cat-file", "-e", f"{rev}^{{commit}}"], timeout=15)
    if probe.returncode == 0:
        return
    run_cmd(["git", "fetch", "--no-tags", "--depth=1", "origin", rev], timeout=90)


def _git_show(rev: str, rel_path: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _ensure_git_rev(rev)
    proc = run_cmd(["git", "show", f"{rev}:{rel_path}"], timeout=30)
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return False
    dest.write_text(proc.stdout or "", encoding="utf-8")
    return True


def _extract_selftest_rtl(root: Path) -> dict[str, Path] | None:
    """Pull #11 CSR / #27 TLB / #21 pyc_reg when those objects exist locally."""
    pyc = root / "pyc_lib"
    ok = True
    ok &= _git_show("1293a5bf", "rtl/pyc_lib/pyc_reg.v", pyc / "pyc_reg.v")
    files = {
        "csr_prod": root / "csr" / "ub_csr_product_x4_vl2.v",
        "csr_hooks": root / "csr" / "hooks" / "ub_csr_product_x4_vl2.v",
        "tlb_prod": root / "mem" / "ub_mem_tlb.v",
        "tlb_hooks": root / "mem" / "hooks" / "ub_mem_tlb.v",
        "bcrc": root / "dll" / "ub_dll_bcrc.v",
        "pyc_reg": pyc / "pyc_reg.v",
    }
    ok &= _git_show("bfcd0b0", "rtl/csr/ub_csr_product_x4_vl2.v", files["csr_prod"])
    ok &= _git_show(
        "bfcd0b0", "rtl/csr/hooks/ub_csr_product_x4_vl2.v", files["csr_hooks"]
    )
    ok &= _git_show("19e9f292", "rtl/mem/ub_mem_tlb.v", files["tlb_prod"])
    ok &= _git_show("19e9f292", "rtl/mem/hooks/ub_mem_tlb.v", files["tlb_hooks"])
    if not _git_show("cc0013c", "rtl/dll/ub_dll_bcrc.v", files["bcrc"]):
        _git_show("e65ff5e", "rtl/gen/dll/ub_dll_bcrc.v", files["bcrc"])
    if not files["csr_prod"].is_file() or not files["pyc_reg"].is_file():
        return None
    stub = root / "cmn" / "ub_cmn_mem_1r1w_d64w109.v"
    stub.parent.mkdir(parents=True)
    # Body (not blackbox) so SAT can import the cell. Same stub on both sides.
    stub.write_text(
        "module ub_cmn_mem_1r1w_d64w109 (\n"
        "  input core_clk, input we, input [5:0] waddr, input [108:0] wdata,\n"
        "  input re, input [5:0] raddr, output reg [108:0] rdata\n"
        ");\n"
        "  always @(posedge core_clk) if (re) rdata <= wdata;\n"
        "endmodule\n",
        encoding="utf-8",
    )
    files["cmn_stub"] = stub
    return files


def _fake_hooks_xor_bit(
    dest: Path,
    module: str,
    gold_src: Path,
    ports: list[tuple[str, str, str]],
    bus: str,
    extra_inputs: list[str],
) -> None:
    """HOOKS wrapper around a renamed gold that xors one bit of *bus*."""
    gold = gold_src.read_text(encoding="utf-8").replace(
        f"module {module}", f"module {module}_gold", 1
    )
    names = [n for _k, n, _p in ports] + extra_inputs
    lines = [
        gold,
        f"module {module} (",
        "  " + ",\n  ".join(names),
        ");",
    ]
    for kind, name, packed in ports:
        rng = f"{packed} " if packed else ""
        lines.append(f"  {kind} {rng}{name};")
    for name in extra_inputs:
        lines.append(f"  input {name};")
    conns: list[str] = []
    packed_bus = next((p for _k, n, p in ports if n == bus), "")
    if packed_bus:
        hi = packed_bus.strip("[]").split(":")[0]
        conns.append(f".{bus}({{{bus}[{hi}:1], ~{bus}[0]}})")
    else:
        conns.append(f".{bus}(~{bus})")
    for _k, name, _p in ports:
        if name != bus:
            conns.append(f".{name}({name})")
    lines.append(f"  {module}_gold u_g (")
    lines.append("    " + ",\n    ".join(conns))
    lines.append("  );")
    lines.append("endmodule")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_equiv_real_csr_tlb() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        files = _extract_selftest_rtl(Path(tmp))
        if files is None:
            print(
                "SELFTEST SKIP equiv-real-csr-tlb: "
                "#11/#21/#27 blobs not in this clone"
            )
            return
        inc = [files["pyc_reg"].parent]
        csr_hits = compare_ports(
            "ub_csr_product_x4_vl2",
            files["csr_prod"],
            files["csr_hooks"],
            ["tb_test_mode"],
            incdirs=inc,
        )
        if csr_hits:
            _fail("ports-csr-#11", csr_hits[0].message)
        print("SELFTEST PASS ports-csr-#11: Yosys PRODUCT/HOOKS (no eaten input/output)")
        csr = run_equiv(
            "ub_csr_product_x4_vl2",
            files["csr_prod"],
            files["csr_hooks"],
            ["tb_test_mode"],
            incdirs=inc,
        )
        if csr is not None:
            _fail("equiv-csr-#11", csr.message)
        print("SELFTEST PASS equiv-csr-#11: PRODUCT≡HOOKS (tb_test_mode tied)")
        ports = parse_port_decls(
            files["csr_prod"], incdirs=inc, module="ub_csr_product_x4_vl2"
        )
        fake = Path(tmp) / "csr_fake.v"
        _fake_hooks_xor_bit(
            fake,
            "ub_csr_product_x4_vl2",
            files["csr_prod"],
            ports,
            "csr_addr",
            ["tb_test_mode"],
        )
        bad = run_equiv(
            "ub_csr_product_x4_vl2",
            files["csr_prod"],
            fake,
            ["tb_test_mode"],
            incdirs=inc,
        )
        if bad is None:
            _fail("equiv-csr-#11-flip", "csr_addr[0] flipped HOOKS must fail")
        print("SELFTEST PASS equiv-csr-#11-flip: fake bus bit fail")

        if files.get("bcrc") and files["bcrc"].is_file():
            bcrc_hooks = Path(tmp) / "bcrc_hooks.v"
            bcrc_hooks.write_text(files["bcrc"].read_text(encoding="utf-8"), encoding="utf-8")
            bp = compare_ports(
                "ub_dll_bcrc", files["bcrc"], bcrc_hooks, None, incdirs=inc
            )
            if bp:
                _fail("ports-bcrc", bp[0].message)
            print("SELFTEST PASS ports-bcrc: Yosys PRODUCT/HOOKS data_in[159:0]")
            bhit = run_equiv("ub_dll_bcrc", files["bcrc"], bcrc_hooks, None, incdirs=inc)
            if bhit is not None:
                _fail("equiv-bcrc", bhit.message)
            print("SELFTEST PASS equiv-bcrc: 160-bit data_in through wrapper")
            bports = parse_port_decls(files["bcrc"], incdirs=inc, module="ub_dll_bcrc")
            if not any(n == "data_in" and p == "[159:0]" for _k, n, p in bports):
                _fail("equiv-bcrc", f"expected data_in[159:0], got {bports}")
            bfake = Path(tmp) / "bcrc_fake.v"
            # Same module shape (no extra hierarchy) so equiv_simple sees crc_word[0].
            text = files["bcrc"].read_text(encoding="utf-8")
            flipped = text.replace(
                "assign crc_word = word_q;",
                "assign crc_word = {word_q[31:1], ~word_q[0]};",
                1,
            )
            if flipped == text:
                _fail("equiv-bcrc-flip", "could not plant crc_word[0] invert")
            bfake.write_text(flipped, encoding="utf-8")
            bbad = run_equiv("ub_dll_bcrc", files["bcrc"], bfake, None, incdirs=inc)
            if bbad is None:
                _fail("equiv-bcrc-flip", "crc_word[0] flipped HOOKS must fail")
            print("SELFTEST PASS equiv-bcrc-flip: fake bus bit fail")

        if files["tlb_prod"].is_file() and files["tlb_hooks"].is_file():
            tlb_extra = hooks_extra_for("ub_mem_tlb")
            th = compare_ports(
                "ub_mem_tlb",
                files["tlb_prod"],
                files["tlb_hooks"],
                tlb_extra,
                incdirs=inc,
            )
            if th:
                _fail("ports-tlb-#27", th[0].message)
            print("SELFTEST PASS ports-tlb-#27: Yosys PRODUCT/HOOKS")
            tports = parse_port_decls(
                files["tlb_prod"], incdirs=inc, module="ub_mem_tlb"
            )
            names = [n for _k, n, _p in tports]
            if "lk_page" not in names:
                _fail("ports-tlb-#27", f"missing lk_page: {names[:12]}")
            # SAT BMC on #27 HOOKS vs PRODUCT exceeds the selftest budget
            # (structurally different pycc + mem stub). Ports are the gate.


def _shuffle_bcrc_ports(src: Path, dest: Path) -> None:
    """Same gold body, port list reordered so order-based cec would see a different AIGER."""
    text = src.read_text(encoding="utf-8")
    shuffled = (
        "module ub_dll_bcrc (\n"
        "  output reg          done,\n"
        "  input  wire         last,\n"
        "  output reg  [31:0]  crc_word,\n"
        "  input  wire [159:0] data_in,\n"
        "  input  wire         valid_in,\n"
        "  input  wire         start,\n"
        "  input  wire         rst_pyc,\n"
        "  input  wire         core_clk\n"
        ");"
    )
    new, n = re.subn(
        r"module\s+ub_dll_bcrc\s*\([^)]*\);",
        shuffled,
        text,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise SystemExit(f"shuffle rewrite failed n={n}")
    dest.write_text(new, encoding="utf-8")


def test_equiv_ref_regpair() -> None:
    """GATE-EQY-004 (4): gold-vs-gold (+ shuffled ports) PASS; fakes and omitted rp_d FAIL."""
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "gate" / "equiv_ref.sh"
    gold = root / "formal" / "dll" / "ref" / "ub_dll_bcrc.sv"
    extra = root / "formal" / "dll" / "negative" / "bcrc_extra_reg.sv"
    carry = root / "formal" / "dll" / "negative" / "bcrc_carry_after_last.sv"
    if not script.is_file() or not gold.is_file():
        _fail("equiv-ref-regpair", "equiv_ref.sh or gold missing")
    env = {**os.environ, "EQUIV_METHODS": "regpair", "EQUIV_TMO": "45"}

    good = run_cmd([str(script), "ub_dll_bcrc", str(gold)], env=env, timeout=90)
    if good.returncode != 0 or "equiv_ref PASS" not in (good.stdout or ""):
        _fail("equiv-ref-regpair-gold", (good.stdout or "")[-400:])
    print("SELFTEST PASS equiv-ref-regpair-gold: gold vs gold")

    with tempfile.TemporaryDirectory() as td:
        shuffled = Path(td) / "bcrc_port_shuffle.sv"
        _shuffle_bcrc_ports(gold, shuffled)
        shuf = run_cmd([str(script), "ub_dll_bcrc", str(shuffled)], env=env, timeout=90)
        if shuf.returncode != 0 or "equiv_ref PASS" not in (shuf.stdout or ""):
            _fail("equiv-ref-regpair-shuffle", (shuf.stdout or "")[-400:])
    print("SELFTEST PASS equiv-ref-regpair-shuffle: shuffled port order")

    omit_env = {**env, "EQUIV_REGPAIR_OMIT_PO": "rp_d_crc", "EQUIV_REGPAIR_OMIT_SIDE": "gold"}
    omit = run_cmd([str(script), "ub_dll_bcrc", str(gold)], env=omit_env, timeout=90)
    omit_out = omit.stdout or ""
    if omit.returncode == 0:
        _fail("equiv-ref-regpair-omit-po", "omitted rp_d_crc must fail")
    if "ports=FAIL" not in omit_out or "rp_d_crc" not in omit_out:
        _fail("equiv-ref-regpair-omit-po", omit_out[-400:])
    print("SELFTEST PASS equiv-ref-regpair-omit-po: missing rp_d_crc listed")

    bad_extra = run_cmd([str(script), "ub_dll_bcrc", str(extra)], env=env, timeout=90)
    if bad_extra.returncode == 0:
        _fail("equiv-ref-regpair-extra", "extra-reg fake must fail")
    if "unmatched" not in (bad_extra.stdout or ""):
        _fail("equiv-ref-regpair-extra", "expected unmatched register listing")
    print("SELFTEST PASS equiv-ref-regpair-extra: unmatched flop")

    bad_carry = run_cmd([str(script), "ub_dll_bcrc", str(carry)], env=env, timeout=90)
    carry_out = bad_carry.stdout or ""
    if bad_carry.returncode == 0:
        _fail("equiv-ref-regpair-carry", "carry-after-last fake must fail")
    if "rp_d_" not in carry_out and "crc_word" not in carry_out:
        _fail("equiv-ref-regpair-carry", f"expected witness on rp_d_* or output: {carry_out[-400:]}")
    print("SELFTEST PASS equiv-ref-regpair-carry: last remainder carried")


def main() -> int:
    tests = [
        test_emit_skip_missing_script,
        test_emit_skip_pycc,
        test_emit_byte_diff,
        test_lock_incomplete,
        test_large_v_committed,
        test_manifest_wrong_sha,
        test_manifest_unproducible,
        test_stray_pyc_reg,
        test_pyc_lib_skip_missing_dir,
        test_pyc_lib_byte_diff,
        test_unlisted_tb_obs,
        test_obs_must_be_output,
        test_sby_bind_missing_signal,
        test_deleted_roster_not_error,
        test_layer_lib_discovered_and_emit,
        test_helper_at_layer_root_is_leaf,
        test_repo_root_on_path_shadows,
        test_lib_helper_splice,
        test_yosys_ansi_ports,
        test_hooks_missing_port,
        test_hooks_wrong_width,
        test_equiv_wide_bus_and_flip,
        test_equiv_real_csr_tlb,
        test_equiv_ref_regpair,
    ]
    for fn in tests:
        fn()
    print(f"gate selftest: PASS ({len(tests)} deliberate-fail cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
