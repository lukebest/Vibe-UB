"""Self-tests for contract hash, private stubs, attests, and role dirs."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contract_hash import contract_sha256
from gatelib import Finding
from private_leaves import (
    OWNED_PATH_MSG,
    WAIVER_UNAPPROVED_MSG,
    WAIVER_UNCHECKED_MSG,
    check_attests,
    check_hash_single,
    check_owned_paths,
    check_role_dirs,
    check_stubs,
    collect_contract_findings,
    discover_contract_files,
    is_gatekeeper_pr,
    is_private_leaf,
    parse_contract_file,
    private_skip_finding,
    validate_contract,
)

VALID_YAML = """\
---
leaf: ub_mem_toy_dec
parent: ub_mem_ptw
clock:
  name: core_clk
  period_ns: 12.412
  reset: rst_pyc
  reset_type: sync
latency:
  kind: registered
  cycles: 1
  max_cycles: 1
ports:
  - {name: core_clk, dir: in, width: 1, desc: clk}
  - {name: rst_pyc, dir: in, width: 1, desc: rst}
params: []
ill_cause_width: 4
assertions:
  - AP_TOY_CLK
  - AP_TOY_HS
status: draft
---

# body
`AP_TOY_CLK` and `AP_TOY_HS` live in the YAML list.
"""


def _fail(name: str, detail: str) -> None:
    print(f"SELFTEST FAIL {name}: {detail}")
    raise SystemExit(1)


def _expect(name: str, findings: list[Finding], rule: str) -> Finding:
    hits = [f for f in findings if f.rule == rule]
    if not hits:
        got = sorted({f.rule for f in findings}) or ["(none)"]
        _fail(name, f"expected {rule}, got {got}")
    print(f"SELFTEST PASS {name}: {rule} ({hits[0].message[:80]})")
    return hits[0]


def _expect_none(name: str, findings: list[Finding], rule: str) -> None:
    hits = [f for f in findings if f.rule == rule]
    if hits:
        _fail(name, f"did not expect {rule}: {hits[0].message}")
    print(f"SELFTEST PASS {name}: no {rule}")


SECTION3_EXACT = """\
## 3. 叶子划分

| 模块 | 本草案叶子 | 类型 | 职责（一句话） |
| --- | --- | --- | --- |
| `ub_mem_ptw` | `ub_mem_ptw` | 结构 | structure |
"""

SECTION3_DESC_ONLY = """\
## 3. 叶子划分

| 模块 | 本草案叶子 | 类型 | 职责（一句话） |
| --- | --- | --- | --- |
| `ub_mem_xlat` | `ub_mem_tlb` | 结构 | 遍历器 `ub_mem_ptw` 只写在描述列 |
"""


def _write_uarch(root: Path, text: str, layer: str = "mem") -> Path:
    path = root / "docs" / "arch" / layer / "UARCH.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_contract(root: Path, text: str, layer: str = "mem", name: str = "ub_mem_toy_dec") -> Path:
    path = root / "docs" / "arch" / layer / "contracts" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    uarch = root / "docs" / "arch" / layer / "UARCH.md"
    if not uarch.is_file():
        _write_uarch(root, SECTION3_EXACT, layer)
    return path


def _register(root: Path, leaf: str) -> None:
    yml = root / "scripts" / "gate" / "private_leaves.yml"
    yml.parent.mkdir(parents=True, exist_ok=True)
    yml.write_text(f"leaves:\n  - {leaf}\n", encoding="utf-8")


def _attest(root: Path, layer: str, leaf: str, digest: str, **over: object) -> Path:
    data = {
        "leaf": leaf,
        "contract_sha256": digest,
        "netlist_sha256": "a" * 64,
        "toolchain_sha256": "b" * 64,
        "clock": {"name": "core_clk", "period_ns": 12.412},
        "cells": 1,
        "area_um2": 0.0,
        "regs": 0,
        "logic_depth": 0,
        "depth_incl_buf": 0,
        "wns_ns": 0.1,
        "crit_path": "public",
        "status": "PASS",
    }
    data.update(over)
    if "clock" in over and isinstance(over["clock"], dict):
        data["clock"] = over["clock"]
    path = root / "reports" / "private" / layer / f"{leaf}.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, val in data.items():
        if key == "clock" and isinstance(val, dict):
            lines.append("clock:")
            lines.append(f"  name: {val['name']}")
            lines.append(f"  period_ns: {val['period_ns']}")
        elif isinstance(val, str):
            lines.append(f"{key}: {val}")
        else:
            lines.append(f"{key}: {val}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_hash_body_stable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        a = _write_contract(root, VALID_YAML, name="ub_mem_toy_a")
        extra = VALID_YAML.replace("# body", "# body\n\nextra paragraph")
        b = _write_contract(root, extra, name="ub_mem_toy_b")
        if contract_sha256(a) != contract_sha256(b):
            _fail("hash-body-stable", "markdown body must not change the digest")
        print("SELFTEST PASS hash-body-stable: same YAML, different prose")


def test_hash_indent_comment_stable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        a = _write_contract(Path(tmp), VALID_YAML, name="ub_mem_toy_a")
        tweaked = VALID_YAML.replace(
            "assertions:\n  - AP_TOY_CLK\n  - AP_TOY_HS",
            "assertions:\n    - AP_TOY_CLK  # clock\n    - AP_TOY_HS",
        )
        b = _write_contract(Path(tmp), tweaked, name="ub_mem_toy_b")
        if contract_sha256(a) != contract_sha256(b):
            _fail("hash-indent-comment-stable", "indent/comments must not change digest")
        print("SELFTEST PASS hash-indent-comment-stable: yaml.safe_load canonical")


def test_hash_assertion_changes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        a = _write_contract(Path(tmp), VALID_YAML, name="ub_mem_toy_a")
        changed = VALID_YAML.replace("  - AP_TOY_HS", "  - AP_TOY_OTHER")
        b = _write_contract(Path(tmp), changed, name="ub_mem_toy_b")
        if contract_sha256(a) == contract_sha256(b):
            _fail("hash-assertion-changes", "editing an assertion must change digest")
        print("SELFTEST PASS hash-assertion-changes: assertion list is in the digest")


def test_parent_ok_and_unknown() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_uarch(root, SECTION3_EXACT)
        path = _write_contract(root, VALID_YAML)
        data, errs = parse_contract_file(path, root)
        if errs or data is None:
            _fail("parent-ok", f"parse failed: {errs}")
        _expect_none("parent-ok", validate_contract(data, root), "PARENT_UNKNOWN")
        bad = VALID_YAML.replace("parent: ub_mem_ptw", "parent: ub_mem_no_such")
        path = _write_contract(root, bad)
        data, _ = parse_contract_file(path, root)
        assert data is not None
        _expect("parent-unknown", validate_contract(data, root), "PARENT_UNKNOWN")


def test_parent_description_not_row() -> None:
    """parent in another row's description column is not an own row."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_uarch(root, SECTION3_DESC_ONLY)
        path = _write_contract(root, VALID_YAML)
        data, errs = parse_contract_file(path, root)
        if errs or data is None:
            _fail("parent-desc-only", f"parse failed: {errs}")
        _expect(
            "parent-desc-only",
            validate_contract(data, root),
            "PARENT_UNKNOWN",
        )


def _set_flag(root: Path, key: str, value: bool) -> None:
    yml = root / "scripts" / "gate" / "private_leaves.yml"
    yml.parent.mkdir(parents=True, exist_ok=True)
    prev = yml.read_text(encoding="utf-8") if yml.is_file() else "leaves: []\n"
    yml.write_text(prev + f"{key}: {str(value).lower()}\n", encoding="utf-8")


def _set_assertions_required(root: Path, value: bool) -> None:
    _set_flag(root, "assertions_required", value)


def test_hash_single_ok_and_dup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        gate = root / "scripts" / "gate"
        gate.mkdir(parents=True)
        (gate / "contract_hash.py").write_text(
            "def contract_sha256(path):\n    return '0' * 64\n",
            encoding="utf-8",
        )
        importer = root / "tb" / "ok_import.py"
        importer.parent.mkdir(parents=True)
        importer.write_text(
            "from scripts.gate.contract_hash import contract_sha256\n"
            "# def contract_sha256 lives in scripts/gate/contract_hash.py\n",
            encoding="utf-8",
        )
        _set_flag(root, "hash_single_required", True)
        hits = check_hash_single(root)
        _expect_none("hash-single-ok", hits, "CONTRACT_HASH_DUP")

        copy = root / "tb" / "mem" / "stub_models" / "contract_hash.py"
        copy.parent.mkdir(parents=True)
        copy.write_text(
            "def contract_sha256(path):\n    return 'deadbeef'\n",
            encoding="utf-8",
        )
        hit = _expect("hash-single-module", check_hash_single(root), "CONTRACT_HASH_DUP")
        if "stub_models/contract_hash.py" not in hit.file:
            _fail("hash-single-module", f"expected stub_models path, got {hit.file}")
        if hit.bucket != "new":
            _fail("hash-single-module", "must be blocking when required")

        impl = root / "scripts" / "impl" / "tests" / "fixtures" / "alt.py"
        impl.parent.mkdir(parents=True)
        impl.write_text("def contract_hash(obj):\n    return obj\n", encoding="utf-8")
        files = {f.file for f in check_hash_single(root) if f.rule == "CONTRACT_HASH_DUP"}
        if "scripts/impl/tests/fixtures/alt.py" not in files:
            _fail("hash-single-def", f"missing def hit, got {sorted(files)}")
        print("SELFTEST PASS hash-single-def: CONTRACT_HASH_DUP on def contract_hash")


def test_hash_single_report_until_main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        copy = root / "tb" / "mem" / "stub_models" / "contract_hash.py"
        copy.parent.mkdir(parents=True)
        copy.write_text("def contract_sha256(path):\n    return ''\n", encoding="utf-8")
        hit = _expect(
            "hash-single-report",
            check_hash_single(root),
            "CONTRACT_HASH_DUP",
        )
        if hit.bucket != "report":
            _fail("hash-single-report", "must be report-only until #47 is on main")


def test_assertions_required_ok_and_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_uarch(root, SECTION3_EXACT)
        _set_assertions_required(root, True)
        path = _write_contract(root, VALID_YAML)
        data, errs = parse_contract_file(path, root)
        if errs or data is None:
            _fail("assert-ok", f"parse failed: {errs}")
        hits = validate_contract(data, root)
        _expect_none("assert-ok", hits, "CONTRACT_FIELD_MISSING")
        _expect_none("assert-ok", hits, "CONTRACT_ASSERT_UNLISTED")
        _expect_none("assert-ok", hits, "CONTRACT_ASSERT_UNUSED")

        missing = VALID_YAML.replace(
            "assertions:\n  - AP_TOY_CLK\n  - AP_TOY_HS\n",
            "",
        )
        path = _write_contract(root, missing)
        data, _ = parse_contract_file(path, root)
        assert data is not None
        hit = _expect(
            "assert-missing",
            validate_contract(data, root),
            "CONTRACT_FIELD_MISSING",
        )
        if hit.bucket != "new":
            _fail("assert-missing", "must be blocking when required")

        empty = VALID_YAML.replace(
            "assertions:\n  - AP_TOY_CLK\n  - AP_TOY_HS\n",
            "assertions: []\n",
        )
        path = _write_contract(root, empty)
        data, _ = parse_contract_file(path, root)
        assert data is not None
        _expect(
            "assert-empty",
            validate_contract(data, root),
            "CONTRACT_FIELD_MISSING",
        )


def test_assertions_unlisted_and_unused() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_uarch(root, SECTION3_EXACT)
        _set_assertions_required(root, True)
        drop = VALID_YAML.replace("  - AP_TOY_HS\n", "")
        path = _write_contract(root, drop)
        data, _ = parse_contract_file(path, root)
        assert data is not None
        _expect(
            "assert-unlisted",
            validate_contract(data, root),
            "CONTRACT_ASSERT_UNLISTED",
        )
        extra = VALID_YAML.replace(
            "  - AP_TOY_HS\n",
            "  - AP_TOY_HS\n  - AP_TOY_GHOST\n",
        )
        path = _write_contract(root, extra)
        data, _ = parse_contract_file(path, root)
        assert data is not None
        _expect(
            "assert-unused",
            validate_contract(data, root),
            "CONTRACT_ASSERT_UNUSED",
        )


def test_assertions_report_until_readme() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_uarch(root, SECTION3_EXACT)
        missing = VALID_YAML.replace(
            "assertions:\n  - AP_TOY_CLK\n  - AP_TOY_HS\n",
            "",
        )
        path = _write_contract(root, missing)
        data, _ = parse_contract_file(path, root)
        assert data is not None
        hit = _expect(
            "assert-report-before-readme",
            validate_contract(data, root),
            "CONTRACT_FIELD_MISSING",
        )
        if hit.bucket != "report":
            _fail("assert-report-before-readme", "must be report-only until README 必填")
        readme = root / "docs" / "arch" / "mem" / "contracts" / "README.md"
        readme.write_text(
            "| 键 | 类型 | 含义 |\n| --- | --- | --- |\n"
            "| `assertions` | 列表 | 必填。参与契约 hash。 |\n",
            encoding="utf-8",
        )
        hit = _expect(
            "assert-blocking-after-readme",
            validate_contract(data, root),
            "CONTRACT_FIELD_MISSING",
        )
        if hit.bucket != "new":
            _fail("assert-blocking-after-readme", "README 必填 must flip to blocking")


def test_comb_budget() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        combo = VALID_YAML.replace(
            "latency:\n  kind: registered\n  cycles: 1\n  max_cycles: 1",
            "latency:\n  kind: combinational\n  cycles: 0\n  max_cycles: 0\ncomb_budget_ns: 3.1",
        )
        path = _write_contract(root, combo)
        data, _ = parse_contract_file(path, root)
        assert data is not None
        hits = validate_contract(data, root)
        _expect_none("comb-budget-ok", hits, "COMB_BUDGET_MISSING")
        _expect_none("comb-budget-ok", hits, "COMB_BUDGET_UNEXPECTED")

        missing = combo.replace("comb_budget_ns: 3.1\n", "")
        path = _write_contract(root, missing)
        data, _ = parse_contract_file(path, root)
        assert data is not None
        _expect("comb-budget-missing", validate_contract(data, root), "COMB_BUDGET_MISSING")

        extra = VALID_YAML.replace(
            "ill_cause_width: 4",
            "comb_budget_ns: 1.0\nill_cause_width: 4",
        )
        path = _write_contract(root, extra)
        data, _ = parse_contract_file(path, root)
        assert data is not None
        _expect(
            "comb-budget-unexpected",
            validate_contract(data, root),
            "COMB_BUDGET_UNEXPECTED",
        )


def test_stub_hash_match_and_mismatch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = _write_contract(root, VALID_YAML)
        _register(root, "ub_mem_toy_dec")
        data, _ = parse_contract_file(path, root)
        assert data is not None
        digest = data["_yaml_hash"]
        stub = root / "rtl" / "mem" / "stub" / "ub_mem_toy_dec.v"
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(
            f"// contract_sha256: {digest}\n// generated-by: scripts/gate/gen_private_stub.py\n"
            "module ub_mem_toy_dec; endmodule\n",
            encoding="utf-8",
        )
        _expect_none("stub-hash-ok", check_stubs(root, [data]), "STUB_HASH_MISMATCH")
        stub.write_text(
            "// contract_sha256: " + ("0" * 64) + "\nmodule ub_mem_toy_dec; endmodule\n",
            encoding="utf-8",
        )
        _expect("stub-hash-mismatch", check_stubs(root, [data]), "STUB_HASH_MISMATCH")


def test_stub_handwritten_report() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = _write_contract(root, VALID_YAML)
        _register(root, "ub_mem_toy_dec")
        data, _ = parse_contract_file(path, root)
        assert data is not None
        stub = root / "rtl" / "mem" / "stub" / "ub_mem_toy_dec.v"
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(
            "// contract_sha256: HANDWRITTEN\nmodule ub_mem_toy_dec; endmodule\n",
            encoding="utf-8",
        )
        hit = _expect("stub-handwritten", check_stubs(root, [data]), "STUB_HANDWRITTEN")
        if hit.bucket != "report":
            _fail("stub-handwritten", "must be report-only until the script is on main")


def test_attest_ok_and_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = _write_contract(root, VALID_YAML)
        _register(root, "ub_mem_toy_dec")
        data, _ = parse_contract_file(path, root)
        assert data is not None
        _expect("attest-missing", check_attests(root, [data]), "ATTEST_MISSING")
        _attest(root, "mem", "ub_mem_toy_dec", data["_yaml_hash"])
        hits = check_attests(root, [data])
        _expect_none("attest-ok", hits, "ATTEST_MISSING")
        _expect_none("attest-ok", hits, "ATTEST_HASH_MISMATCH")
        _expect_none("attest-ok", hits, "ATTEST_CLOCK_MISMATCH")
        _expect_none("attest-ok", hits, "ATTEST_STATUS")
        _expect_none("attest-ok", hits, "ATTEST_WNS")


def test_attest_public_path_not_private_repo() -> None:
    """Public gate reads reports/private/; private-repo attest/ does not count."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = _write_contract(root, VALID_YAML)
        _register(root, "ub_mem_toy_dec")
        data, _ = parse_contract_file(path, root)
        assert data is not None
        digest = data["_yaml_hash"]
        private_repo = root / "attest" / "mem" / "ub_mem_toy_dec.yml"
        private_repo.parent.mkdir(parents=True, exist_ok=True)
        public = _attest(root, "mem", "ub_mem_toy_dec", digest)
        private_repo.write_text(public.read_text(encoding="utf-8"), encoding="utf-8")
        public.unlink()
        hits = check_attests(root, [data])
        hit = _expect(
            "attest-ignores-private-repo-path",
            hits,
            "ATTEST_MISSING",
        )
        if hit.file != "reports/private/mem/ub_mem_toy_dec.yml":
            _fail(
                "attest-ignores-private-repo-path",
                f"public path must be reports/private/..., got {hit.file}",
            )
        if "attest/mem/" in hit.file:
            _fail("attest-ignores-private-repo-path", "must not treat attest/ as public")
        _attest(root, "mem", "ub_mem_toy_dec", digest)
        hits = check_attests(root, [data])
        _expect_none("attest-reports-private-ok", hits, "ATTEST_MISSING")


def test_attest_hash_mismatch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = _write_contract(root, VALID_YAML)
        _register(root, "ub_mem_toy_dec")
        data, _ = parse_contract_file(path, root)
        assert data is not None
        _attest(root, "mem", "ub_mem_toy_dec", "0" * 64)
        _expect(
            "attest-hash-mismatch",
            check_attests(root, [data]),
            "ATTEST_HASH_MISMATCH",
        )


def test_attest_clock_mismatch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = _write_contract(root, VALID_YAML)
        _register(root, "ub_mem_toy_dec")
        data, _ = parse_contract_file(path, root)
        assert data is not None
        _attest(
            root,
            "mem",
            "ub_mem_toy_dec",
            data["_yaml_hash"],
            clock={"name": "core_clk", "period_ns": 9.999},
        )
        _expect(
            "attest-clock-mismatch",
            check_attests(root, [data]),
            "ATTEST_CLOCK_MISMATCH",
        )


def test_attest_status_and_wns() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = _write_contract(root, VALID_YAML)
        _register(root, "ub_mem_toy_dec")
        data, _ = parse_contract_file(path, root)
        assert data is not None
        _attest(root, "mem", "ub_mem_toy_dec", data["_yaml_hash"], status="FAIL")
        _expect("attest-status-fail", check_attests(root, [data]), "ATTEST_STATUS")
        _attest(root, "mem", "ub_mem_toy_dec", data["_yaml_hash"], wns_ns=-0.01)
        _expect("attest-wns-neg", check_attests(root, [data]), "ATTEST_WNS")
        path.unlink()
        # missing field
        att = root / "reports" / "private" / "mem" / "ub_mem_toy_dec.yml"
        att.write_text("leaf: ub_mem_toy_dec\nstatus: PASS\n", encoding="utf-8")
        # parse_contract gone; still registered so attest is checked
        data = {
            "leaf": "ub_mem_toy_dec",
            "_layer": "mem",
            "_yaml_hash": "c" * 64,
            "clock": {"name": "core_clk", "period_ns": 12.412},
        }
        _expect("attest-field-missing", check_attests(root, [data]), "ATTEST_FIELD")


OWNED_TOUCH = [
    "scripts/gate/private_leaves.py",
    ".github/workflows/gate.yml",
    "waivers/formal.yml",
    "docs/rules/verif_gate.md",
]


def test_owned_paths_gatekeeper_ok() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _set_flag(root, "owned_paths_required", True)
        hits = check_owned_paths(
            root,
            OWNED_TOUCH,
            title="gate: S-01(b) private leaves",
            comments="",
        )
        _expect_none("owned-paths-title", hits, "GATE_FILE_TOUCHED")
        _expect_none("owned-paths-title-waiver", hits, "GATE_WAIVER_UNCHECKED")
        if not is_gatekeeper_pr(title="gate: anything"):
            _fail("owned-paths-prefix", "title gate: must be gatekeeper")
        if is_gatekeeper_pr(title="Gate: wrong case"):
            _fail("owned-paths-prefix", "title prefix is case-sensitive gate:")
        if is_gatekeeper_pr(title="feat: leaf-fix"):
            _fail("owned-paths-prefix", "non-gate title must not match")


def test_owned_paths_non_gatekeeper() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _set_flag(root, "owned_paths_required", True)
        hits = check_owned_paths(
            root,
            OWNED_TOUCH,
            title="feat: leaf-fix",
            comments="",
        )
        hit = _expect("owned-paths-neg", hits, "GATE_FILE_TOUCHED")
        if hit.message != OWNED_PATH_MSG:
            _fail("owned-paths-neg", f"message must be exact, got {hit.message!r}")
        files = set(hit.file.split(","))
        expect = {
            "scripts/gate/private_leaves.py",
            ".github/workflows/gate.yml",
        }
        if files != expect:
            _fail("owned-paths-neg", f"file list {sorted(files)} != {sorted(expect)}")
        if "waivers/formal.yml" in files:
            _fail("owned-paths-neg", "waivers/ is the exception, not GATE_FILE_TOUCHED")
        if hit.bucket != "new":
            _fail("owned-paths-neg", "must be blocking when owned_paths_required")
        clean = check_owned_paths(
            root,
            ["docs/rules/verif_gate.md", "rtl/mem/ub_mem_ptw.v"],
            title="feat: leaf-fix",
            comments="",
        )
        _expect_none("owned-paths-unrelated", clean, "GATE_FILE_TOUCHED")
        only_waiver = check_owned_paths(
            root,
            ["waivers/formal.yml"],
            title="feat: leaf-fix",
            comments="GATE-WAIVER-APPROVED: waivers/formal.yml\n",
        )
        _expect_none("owned-paths-waiver-ok", only_waiver, "GATE_FILE_TOUCHED")
        _expect_none("owned-paths-waiver-ok", only_waiver, "GATE_WAIVER_UNAPPROVED")


def test_owned_paths_report_until_main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        hit = _expect(
            "owned-paths-report",
            check_owned_paths(
                root,
                ["scripts/gate/contract_check.py"],
                title="user/pr",
                comments="",
            ),
            "GATE_FILE_TOUCHED",
        )
        if hit.bucket != "report":
            _fail("owned-paths-report", "must be report-only until #47 is on main")


def test_owned_paths_waiver_approval() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        unchecked = check_owned_paths(
            root,
            ["waivers/lint.yml"],
            title="feat: add lint waiver",
        )
        hit = _expect("waiver-unchecked", unchecked, "GATE_WAIVER_UNCHECKED")
        if hit.message != WAIVER_UNCHECKED_MSG:
            _fail("waiver-unchecked", f"message {hit.message!r}")
        if hit.bucket != "report":
            _fail("waiver-unchecked", "API-not-wired must stay report-only")
        missing = check_owned_paths(
            root,
            ["waivers/lint.yml"],
            title="feat: add lint waiver",
            comments="LGTM\n",
        )
        hit = _expect("waiver-unapproved", missing, "GATE_WAIVER_UNAPPROVED")
        if hit.message != WAIVER_UNAPPROVED_MSG:
            _fail("waiver-unapproved", f"message {hit.message!r}")
        if hit.bucket != "report":
            _fail("waiver-unapproved", "until API is wired this stays report-only")
        if hit.file != "waivers/lint.yml":
            _fail("waiver-unapproved", f"id must be path, got {hit.file}")


def test_role_cross_and_ok() -> None:
    _expect(
        "role-cross",
        check_role_dirs(["design/a.py", "verif/b.py"], title="[design] work"),
        "ROLE_CROSS",
    )
    hits = check_role_dirs(
        ["design/a.py", "public/shared.md"], title="[design] one role"
    )
    _expect_none("role-one-plus-public", hits, "ROLE_CROSS")
    hits = check_role_dirs(["scripts/gate/x.py", "docs/rules/verif_gate.md"])
    _expect_none("role-public-tree", hits, "ROLE_CROSS")


def test_private_skip_helper() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _register(root, "ub_mem_toy_dec")
        if not is_private_leaf("ub_mem_toy_dec", root):
            _fail("private-skip", "registered leaf must match")
        if not is_private_leaf("ub_mem_toy_dec_d4", root):
            _fail("private-skip", "variant suffix must match")
        if is_private_leaf("ub_mem_ptw", root):
            _fail("private-skip", "unrelated leaf must not match")
        f = private_skip_finding("lint", "ub_mem_toy_dec", "rtl/mem/stub/ub_mem_toy_dec.v")
        if f.rule != "PRIVATE_SKIP" or f.bucket != "report":
            _fail("private-skip", "PRIVATE_SKIP must be report-only")
        print("SELFTEST PASS private-skip: helper + variant prefix")


PCS_SECTION3_EXACT = """\
## 3. 叶子划分

| 模块 | 本草案叶子 | 类型 | 职责（一句话） |
| --- | --- | --- | --- |
| `ub_pcs_amctl_rx` | `ub_pcs_amctl_rx` | 结构 | AMCTL RX parent |
"""

PCS_SECTION3_DESC_ONLY = """\
## 3. 叶子划分

| 模块 | 本草案叶子 | 类型 | 职责（一句话） |
| --- | --- | --- | --- |
| `ub_pcs_deskew` | `ub_pcs_deskew` | 结构 | 父级 `ub_pcs_amctl_rx` 只写在描述列 |
"""


def test_scan_includes_pcs_layer() -> None:
    """#45-shaped fixture: pcs contract + pcs UARCH.md §3, not mem."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_uarch(root, SECTION3_EXACT, layer="mem")
        pcs = VALID_YAML.replace("ub_mem_toy_dec", "ub_pcs_amctl_cw_dec").replace(
            "parent: ub_mem_ptw", "parent: ub_pcs_amctl_rx"
        )
        path = _write_contract(
            root, pcs, layer="pcs", name="ub_pcs_amctl_cw_dec"
        )
        found = [p.name for p in discover_contract_files(root)]
        if "ub_pcs_amctl_cw_dec.md" not in found:
            _fail("scan-pcs", f"pcs contract not scanned: {found}")

        _write_uarch(root, PCS_SECTION3_EXACT, layer="pcs")
        data, errs = parse_contract_file(path, root)
        if errs or data is None:
            _fail("scan-pcs-parent-ok", f"parse failed: {errs}")
        if data.get("_layer") != "pcs":
            _fail("scan-pcs-parent-ok", f"layer={data.get('_layer')}")
        hits = validate_contract(data, root)
        _expect_none("scan-pcs-parent-ok", hits, "PARENT_UNKNOWN")

        _write_uarch(root, PCS_SECTION3_DESC_ONLY, layer="pcs")
        data, _ = parse_contract_file(path, root)
        assert data is not None
        _expect(
            "scan-pcs-parent-desc-only",
            validate_contract(data, root),
            "PARENT_UNKNOWN",
        )

        (root / "docs" / "arch" / "pcs" / "UARCH.md").unlink()
        data, _ = parse_contract_file(path, root)
        assert data is not None
        hit = _expect(
            "scan-pcs-ignores-mem-uarch",
            validate_contract(data, root),
            "PARENT_UNKNOWN",
        )
        if "docs/arch/pcs/UARCH.md" not in hit.message:
            _fail(
                "scan-pcs-ignores-mem-uarch",
                f"must name pcs UARCH, got {hit.message}",
            )
        print("SELFTEST PASS scan-pcs: docs/arch/pcs/UARCH.md §3 is the pcs parent table")


def run_all() -> None:
    tests = [
        test_hash_body_stable,
        test_hash_indent_comment_stable,
        test_hash_assertion_changes,
        test_parent_ok_and_unknown,
        test_parent_description_not_row,
        test_hash_single_ok_and_dup,
        test_hash_single_report_until_main,
        test_assertions_required_ok_and_missing,
        test_assertions_unlisted_and_unused,
        test_assertions_report_until_readme,
        test_comb_budget,
        test_stub_hash_match_and_mismatch,
        test_stub_handwritten_report,
        test_attest_ok_and_missing,
        test_attest_public_path_not_private_repo,
        test_attest_hash_mismatch,
        test_attest_clock_mismatch,
        test_attest_status_and_wns,
        test_owned_paths_gatekeeper_ok,
        test_owned_paths_non_gatekeeper,
        test_owned_paths_report_until_main,
        test_owned_paths_waiver_approval,
        test_role_cross_and_ok,
        test_private_skip_helper,
        test_scan_includes_pcs_layer,
    ]
    for fn in tests:
        fn()
    print(f"private-leaf selftest: PASS ({len(tests)} groups)")


if __name__ == "__main__":
    run_all()
