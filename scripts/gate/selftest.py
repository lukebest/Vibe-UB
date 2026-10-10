#!/usr/bin/env python3
"""Deliberate-fail fixtures: each new gate check must catch a planted violation."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from formal_bind import check_formal_binds
from gatelib import (
    Finding,
    collect_lock_completeness_findings,
    mark_deleted_findings,
    sha256_file,
)
from hooks_port_consistency import compare_ports
from large_mem_manifest import check_large_mem_manifest
from pyc_lib_check import check_pyc_lib
from rtl_emit_consistency import compare_emitted_rtl, emit_unavailable_findings


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
    ]
    for fn in tests:
        fn()
    print(f"gate selftest: PASS ({len(tests)} deliberate-fail cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
