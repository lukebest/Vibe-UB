#!/usr/bin/env python3
"""E2E self-tests for private-leaf quick-synth (Yosys + OpenSTA + Sky130 hd).

(a) attest mode on a fake contract + tiny netlist; exact YAML field set
(b) parent instantiating a stub → PRIVATE_SKIP, stub area = 0
(c) crit_path redaction (public vs 私有叶子内部; no net names in attest)
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_HASH = Path(__file__).resolve().parent / "fixtures" / "contract_hash.py"
sys.path.insert(0, str(SCRIPT_DIR))

from priv_leaf import (  # noqa: E402
    ATTEST_FIELDS,
    CRIT_PATH_PRIVATE,
    CRIT_PATH_PUBLIC,
    attest_field_names,
    load_yaml_mapping,
)
from quick_synth import main as qs_main  # noqa: E402

REG_CONTRACT = """```yaml
leaf: ub_qs_priv_reg
parent: ub_qs_parent
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
  - {name: raw, dir: in, width: 4, desc: in}
  - {name: dec, dir: out, width: 4, desc: out}
params: []
ill_cause_width: 4
status: draft
```

# test contract
"""

COMBO_CONTRACT = """```yaml
leaf: ub_qs_priv_combo
parent: ub_qs_parent
clock:
  name: core_clk
  period_ns: 12.412
  reset: rst_pyc
  reset_type: sync
latency:
  kind: combinational
  cycles: 0
  max_cycles: 0
comb_budget_ns: 3.1
ports:
  - {name: core_clk, dir: in, width: 1, desc: clk}
  - {name: rst_pyc, dir: in, width: 1, desc: rst}
  - {name: raw, dir: in, width: 4, desc: in}
  - {name: dec, dir: out, width: 4, desc: out}
params: []
ill_cause_width: 4
status: draft
```

# combo test contract
"""

STUB_CONTRACT = """```yaml
leaf: ub_qs_priv_leaf
parent: ub_qs_parent
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
  - {name: a, dir: in, width: 8, desc: in}
  - {name: y, dir: out, width: 8, desc: out}
params: []
ill_cause_width: 4
status: draft
```

# stub parent test
"""

REG_NETLIST = """module ub_qs_priv_reg (
  input core_clk,
  input rst_pyc,
  input [3:0] raw,
  output [3:0] dec
);
  reg [3:0] a;
  reg [3:0] b;
  wire [3:0] mid = a ^ {a[0], a[3:1]} ^ {a[1:0], a[3:2]} ^ ~a;
  always @(posedge core_clk) begin
    if (rst_pyc) begin
      a <= 4'b0;
      b <= 4'b0;
    end else begin
      a <= raw;
      b <= mid;
    end
  end
  assign dec = b;
endmodule
"""

COMBO_NETLIST = """module ub_qs_priv_combo (
  input core_clk,
  input rst_pyc,
  input [3:0] raw,
  output [3:0] dec
);
  assign dec = raw ^ 4'h5;
endmodule
"""

FAT_STUB = """// contract_sha256: HANDWRITTEN
// placeholder internals must not count toward area
module ub_qs_priv_leaf (
  input core_clk,
  input rst_pyc,
  input [7:0] a,
  output [7:0] y
);
  wire [63:0] fat;
  assign fat[0] = a[0];
  genvar i;
  generate
    for (i = 1; i < 64; i = i + 1) begin : g
      assign fat[i] = fat[i-1] ^ a[i%8] & a[(i+1)%8];
    end
  endgenerate
  assign y = fat[63:56] ^ fat[7:0] ^ a;
endmodule
"""

PARENT = """module ub_qs_parent (
  input core_clk,
  input rst_pyc,
  input [7:0] a,
  output [7:0] z
);
  wire [7:0] y0;
  wire [7:0] y1;
  ub_qs_priv_leaf u0 (
    .core_clk(core_clk), .rst_pyc(rst_pyc), .a(a), .y(y0)
  );
  ub_qs_priv_leaf u1 (
    .core_clk(core_clk), .rst_pyc(rst_pyc), .a(y0), .y(y1)
  );
  assign z = y1 ^ a;
endmodule
"""

SPEC_SNIP = (
    "F_CORE = 2.578125e9 / 32 ≈ 80.57 MHz. Sky130 proxy.\n"
)

LOCK = "# test TOOLCHAIN.lock\npin = 1\n"


def _fail(name: str, detail: str) -> None:
    print(f"PRIVATE TEST FAIL {name}: {detail}", file=sys.stderr)
    raise SystemExit(1)


def _ok(name: str, detail: str = "") -> None:
    extra = f" ({detail})" if detail else ""
    print(f"PRIVATE TEST PASS {name}{extra}")


def _liberty() -> Path:
    raw = os.environ.get("SKY130_HD_LIB", "")
    if raw and Path(raw).is_file():
        return Path(raw)
    _fail("liberty", "SKY130_HD_LIB is not set; run via scripts/impl/quick_synth.sh --self-check")
    raise AssertionError


def _prep_repo(td: Path) -> Path:
    root = td
    (root / "scripts" / "gate").mkdir(parents=True)
    shutil.copy(FIXTURE_HASH, root / "scripts" / "gate" / "contract_hash.py")
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "SPEC.md").write_text(SPEC_SNIP, encoding="utf-8")
    (root / "TOOLCHAIN.lock").write_text(LOCK, encoding="utf-8")
    (root / "rtl" / "pyc_lib").mkdir(parents=True)
    return root


def _write_contract(root: Path, name: str, text: str) -> Path:
    path = root / "docs" / "arch" / "mem" / "contracts" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _run(argv: list[str]) -> int:
    try:
        return qs_main(argv)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1


def test_attest_fields(liberty: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="qs_att_") as tmp:
        root = _prep_repo(Path(tmp))
        contract = _write_contract(root, "ub_qs_priv_reg", REG_CONTRACT)
        netlist = root / "rtl" / "mem" / "ub_qs_priv_reg.v"
        netlist.parent.mkdir(parents=True, exist_ok=True)
        netlist.write_text(REG_NETLIST, encoding="utf-8")
        out = root / "attest.yml"
        scratch = root / "scratch"
        rc = _run(
            [
                "--repo",
                str(root),
                "--work-tree",
                str(root),
                "--attest",
                "ub_qs_priv_reg",
                "--contract",
                str(contract),
                "--netlist",
                str(netlist),
                "--out",
                str(out),
                "--scratch",
                str(scratch),
                "--liberty",
                str(liberty),
            ]
        )
        if rc != 0:
            _fail("attest-e2e", f"exit {rc}")
        if not out.is_file():
            _fail("attest-e2e", "no YAML written")
        text = out.read_text(encoding="utf-8")
        keys = attest_field_names(text)
        if keys != list(ATTEST_FIELDS):
            _fail("attest-e2e", f"fields {keys} != {list(ATTEST_FIELDS)}")
        data = load_yaml_mapping(text)
        if data["leaf"] != "ub_qs_priv_reg":
            _fail("attest-e2e", f"leaf {data['leaf']}")
        if data["clock"]["name"] != "core_clk" or data["clock"]["period_ns"] != 12.412:
            _fail("attest-e2e", f"clock {data['clock']}")
        if data["status"] not in {"PASS", "FAIL"}:
            _fail("attest-e2e", f"status {data['status']}")
        if data["crit_path"] not in {CRIT_PATH_PUBLIC, CRIT_PATH_PRIVATE}:
            _fail("attest-e2e", f"crit_path {data['crit_path']}")
        if "Startpoint" in text or "sky130" in text or "/" in data["crit_path"]:
            _fail("attest-e2e", "attest leaked a path or net name")
        if not data["contract_sha256"] or len(str(data["contract_sha256"])) != 64:
            _fail("attest-e2e", "contract_sha256 missing")
        _ok("attest-e2e", f"status={data['status']} crit_path={data['crit_path']}")


def test_parent_stub_skip(liberty: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="qs_par_") as tmp:
        root = _prep_repo(Path(tmp))
        _write_contract(root, "ub_qs_priv_leaf", STUB_CONTRACT)
        stub = root / "rtl" / "mem" / "stub" / "ub_qs_priv_leaf.v"
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(FAT_STUB, encoding="utf-8")
        parent = root / "rtl" / "mem" / "ub_qs_parent.v"
        parent.write_text(PARENT, encoding="utf-8")
        out = root / "qs_out"
        rc = _run(
            [
                "--repo",
                str(root),
                "--work-tree",
                str(root),
                "--tops",
                "ub_qs_parent",
                "--out",
                str(out),
                "--liberty",
                str(liberty),
            ]
        )
        if rc != 0:
            logs = list(out.rglob("yosys.log"))
            excerpt = logs[0].read_text(errors="replace")[-600:] if logs else ""
            _fail("parent-stub-skip", f"exit {rc}\n{excerpt}")
        import json

        payload = json.loads((out / "results.json").read_text(encoding="utf-8"))
        rows = payload["results"]
        skip = [r for r in rows if r.get("private_skip")]
        parent_rows = [r for r in rows if r.get("top") == "ub_qs_parent"]
        if not skip or skip[0]["top"] != "ub_qs_priv_leaf":
            _fail("parent-stub-skip", f"PRIVATE_SKIP rows {skip}")
        if skip[0].get("area_um2") not in (0, 0.0):
            _fail("parent-stub-skip", f"skip area {skip[0].get('area_um2')}")
        if int(skip[0].get("n_inst") or 0) != 2:
            _fail("parent-stub-skip", f"n_inst {skip[0].get('n_inst')}")
        if not parent_rows or not parent_rows[0].get("ok"):
            _fail("parent-stub-skip", f"parent {parent_rows}")
        pcells = parent_rows[0].get("cells_mapped")
        parea = parent_rows[0].get("area_um2") or 0
        if pcells is None or pcells > 40:
            _fail(
                "parent-stub-skip",
                f"parent cells {pcells} look like stub internals were mapped",
            )
        if parea > 400:
            _fail("parent-stub-skip", f"parent area {parea} includes stub logic")
        totals = payload.get("product_totals") or {}
        if abs(float(totals.get("area_um2") or 0) - float(parea)) > 1e-6:
            _fail("parent-stub-skip", f"totals include skip area {totals}")

        att_dir = root / "reports" / "private" / "mem"
        att_dir.mkdir(parents=True, exist_ok=True)
        (att_dir / "ub_qs_priv_leaf.yml").write_text(
            "\n".join(
                [
                    "leaf: ub_qs_priv_leaf",
                    "contract_sha256: " + ("a" * 64),
                    "netlist_sha256: " + ("b" * 64),
                    "toolchain_sha256: " + ("c" * 64),
                    "clock:",
                    "  name: core_clk",
                    "  period_ns: 12.412",
                    "cells: 4",
                    "area_um2: 10.0",
                    "regs: 1",
                    "logic_depth: 1",
                    "depth_incl_buf: 1",
                    "wns_ns: 1.0",
                    "crit_path: public",
                    "status: PASS",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        out2 = root / "qs_out2"
        rc = _run(
            [
                "--repo",
                str(root),
                "--work-tree",
                str(root),
                "--tops",
                "ub_qs_parent",
                "--out",
                str(out2),
                "--liberty",
                str(liberty),
            ]
        )
        if rc != 0:
            _fail("parent-ci-area", f"exit {rc}")
        payload = json.loads((out2 / "results.json").read_text(encoding="utf-8"))
        skip = [r for r in payload["results"] if r.get("private_skip")][0]
        if abs(float(skip.get("private_ci_area_um2") or 0) - 20.0) > 1e-6:
            _fail("parent-ci-area", f"私有 CI 出数 {skip.get('private_ci_area_um2')}")
        if skip.get("private_ci_label") != "私有 CI 出数":
            _fail("parent-ci-area", f"label {skip.get('private_ci_label')}")
        _ok("parent-stub-skip", f"parent cells={pcells} area={parea} n_inst=2")


def test_crit_path_redaction(liberty: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="qs_crit_") as tmp:
        root = _prep_repo(Path(tmp))
        combo_c = _write_contract(root, "ub_qs_priv_combo", COMBO_CONTRACT)
        reg_c = _write_contract(root, "ub_qs_priv_reg", REG_CONTRACT)
        combo_v = root / "combo.v"
        reg_v = root / "reg.v"
        combo_v.write_text(COMBO_NETLIST, encoding="utf-8")
        reg_v.write_text(REG_NETLIST, encoding="utf-8")

        combo_out = root / "combo.yml"
        rc = _run(
            [
                "--repo",
                str(root),
                "--work-tree",
                str(root),
                "--attest",
                "ub_qs_priv_combo",
                "--contract",
                str(combo_c),
                "--netlist",
                str(combo_v),
                "--out",
                str(combo_out),
                "--scratch",
                str(root / "sc_combo"),
                "--liberty",
                str(liberty),
            ]
        )
        if rc != 0:
            _fail("crit-combo", f"exit {rc}")
        combo = load_yaml_mapping(combo_out.read_text(encoding="utf-8"))
        if combo["crit_path"] != CRIT_PATH_PUBLIC:
            _fail("crit-combo", f"expected public, got {combo['crit_path']}")
        if any(tok in combo_out.read_text(encoding="utf-8") for tok in ("Startpoint", "sky130_fd")):
            _fail("crit-combo", "attest leaked STA names")

        reg_out = root / "reg.yml"
        rc = _run(
            [
                "--repo",
                str(root),
                "--work-tree",
                str(root),
                "--attest",
                "ub_qs_priv_reg",
                "--contract",
                str(reg_c),
                "--netlist",
                str(reg_v),
                "--out",
                str(reg_out),
                "--scratch",
                str(root / "sc_reg"),
                "--liberty",
                str(liberty),
            ]
        )
        if rc != 0:
            _fail("crit-reg", f"exit {rc}")
        reg = load_yaml_mapping(reg_out.read_text(encoding="utf-8"))
        if reg["crit_path"] != CRIT_PATH_PRIVATE:
            _fail("crit-reg", f"expected 私有叶子内部, got {reg['crit_path']}")
        body = reg_out.read_text(encoding="utf-8")
        if "Startpoint" in body or "sky130_fd" in body or "/D" in body:
            _fail("crit-reg", "attest leaked STA names")
        _ok(
            "crit-path-redaction",
            f"combo={combo['crit_path']} reg={reg['crit_path']}",
        )


def main() -> int:
    if not shutil.which("yosys") or not shutil.which("sta"):
        print("PRIVATE TEST FAIL: yosys/sta missing", file=sys.stderr)
        return 1
    liberty = _liberty()
    test_attest_fields(liberty)
    test_parent_stub_skip(liberty)
    test_crit_path_redaction(liberty)
    print("private-leaf E2E: PASS (3 groups)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
