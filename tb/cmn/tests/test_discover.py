"""SPEC §2.2 variant discovery — tag / sidecar / comments, no Verilator -G."""

from __future__ import annotations

from pathlib import Path

from tb.cmn.discover import (
    LEAF,
    discover_by_netlist,
    discover_variants,
    parse_variant_file,
    require_variant_ports,
    rtl_sim_skip_reason,
)
from tb.cmn.harness.emit_wrapper import TOPLEVEL, emit_wrapper
from tb.cmn.ports import (
    CLK_MISMATCH_ZH,
    CLK_PORT,
    LeafPortError,
    RST_FORBIDDEN_ZH,
    WMASK_FORBIDDEN_ZH,
    WMASK_MISSING_ZH,
    WMASK_WIDTH_ZH,
    check_leaf_ports,
    check_wmask_port,
    parse_module_ports,
)


def _write_leaf(path: Path, module: str, aw: int, width: int, header: str = "") -> Path:
    path.write_text(
        f"""{header}
module {module} (
  input  wire clk,
  input  wire we,
  input  wire [{aw}-1:0] waddr,
  input  wire [{width}-1:0] wdata,
  input  wire re,
  input  wire [{aw}-1:0] raddr,
  output reg  [{width}-1:0] rdata
);
endmodule
""",
        encoding="utf-8",
    )
    return path


def test_parse_d5w8_tag(tmp_path: Path):
    path = _write_leaf(tmp_path / f"{LEAF}_d5w8.v", f"{LEAF}_d5w8", 3, 8)
    var = parse_variant_file(path, netlist="product")
    assert var is not None
    assert var.depth == 5 and var.width == 8
    assert var.wmask_w == 8 and var.nseg == 1
    assert var.module == f"{LEAF}_d5w8"
    assert var.tag == "d5w8"
    assert var.source == "tag"
    assert var.aw == 3
    assert var.ports == ("clk", "we", "waddr", "wdata", "re", "raddr", "rdata")


def test_parse_d8_w16_tag(tmp_path: Path):
    path = _write_leaf(tmp_path / f"{LEAF}_d8_w16.v", f"{LEAF}_d8_w16", 3, 16)
    var = parse_variant_file(path, netlist="product")
    assert var is not None
    assert (var.depth, var.width) == (8, 16)


def test_parse_sidecar_json(tmp_path: Path):
    path = _write_leaf(tmp_path / f"{LEAF}.v", LEAF, 3, 8)
    path.with_suffix(".json").write_text(
        '{"DEPTH": 5, "WIDTH": 8, "tag": "default"}', encoding="utf-8"
    )
    var = parse_variant_file(path, netlist="product")
    assert var is not None
    assert (var.depth, var.width) == (5, 8)
    assert var.source == "sidecar"


def test_parse_header_comment(tmp_path: Path):
    path = _write_leaf(
        tmp_path / f"{LEAF}.v",
        LEAF,
        3,
        9,
        header="// DEPTH=5 WIDTH=9  CODING_STYLE §10",
    )
    var = parse_variant_file(path, netlist="product")
    assert var is not None
    assert (var.depth, var.width) == (5, 9)
    assert var.source == "comment"


def test_unknown_file_is_ignored(tmp_path: Path):
    path = _write_leaf(tmp_path / "ub_other.v", "ub_other", 3, 8)
    assert parse_variant_file(path, netlist="product") is None


def test_discover_product_and_hooks(tmp_path: Path):
    cmn = tmp_path / "rtl" / "cmn"
    hooks = cmn / "hooks"
    hooks.mkdir(parents=True)
    _write_leaf(cmn / f"{LEAF}_d5w8.v", f"{LEAF}_d5w8", 3, 8)
    _write_leaf(hooks / f"{LEAF}_d5w8.v", f"{LEAF}_d5w8", 3, 8)
    _write_leaf(cmn / f"{LEAF}_d8w16.v", f"{LEAF}_d8w16", 3, 16)
    found = discover_variants(tmp_path)
    assert {v.id for v in found} >= {
        f"product:{LEAF}_d5w8:d5w8",
        f"hooks:{LEAF}_d5w8:d5w8",
        f"product:{LEAF}_d8w16:d8w16",
    }
    assert len(discover_by_netlist("product", tmp_path)) == 2
    assert len(discover_by_netlist("hooks", tmp_path)) == 1


def test_skip_reason_without_rtl(tmp_path: Path):
    (tmp_path / "rtl").mkdir()
    reason = rtl_sim_skip_reason(tmp_path)
    assert reason is not None
    assert "rtl/cmn" in reason
    assert "self-check" in reason.lower() or "Python" in reason


def test_emit_wrapper_bakes_constants_no_dut_parameter(tmp_path: Path):
    dest = tmp_path / "wrap.sv"
    emit_wrapper(
        dest,
        dut_module=f"{LEAF}_d5w8",
        depth=5,
        width=8,
        assert_no_uninit_read=True,
        tb_check=True,
    )
    text = dest.read_text(encoding="utf-8")
    assert f"module {TOPLEVEL}" in text
    assert f"{LEAF}_d5w8 u_dut" in text
    assert f"{LEAF}_d5w8 #(" not in text
    assert "u_dut (" in text
    assert "localparam integer DEPTH = 5" in text
    assert "localparam integer WIDTH = 8" in text
    assert "ub_cmn_mem_1r1w_if_props" in text
    assert ".ASSERT_NO_UNINIT_READ(ASSERT_NO_UNINIT_READ)" in text
    assert f"input  wire             {CLK_PORT}" in text
    assert f".{CLK_PORT} ({CLK_PORT})" in text
    assert "rst_n" not in text
    assert "rst_pyc" not in text
    assert f"input  wire             clk\n" not in text
    assert ".clk   (clk)" not in text
    assert "localparam integer WMASK_W = 8" in text
    assert ".wmask    (1'b1)" in text
    assert ".wmask (wmask)" not in text
    assert "input  wire [1-1:0] wmask" not in text
    assert ".WMASK_W(WMASK_W)" in text


def test_parse_parameterized_formal_if_props():
    text = """
module ub_cmn_mem_1r1w_if_props #(
  parameter DEPTH = 5,
  parameter WIDTH = 8
) (
  input  wire             core_clk,
  input  wire             we,
  input  wire [AW-1:0]    waddr,
  input  wire [WIDTH-1:0] wdata,
  input  wire             re,
  input  wire [AW-1:0]    raddr,
  input  wire [WIDTH-1:0] rdata,
  output wire [AW-1:0]    f_addr,
  output wire             f_written
);
endmodule
"""
    ports = parse_module_ports(text, "ub_cmn_mem_1r1w_if_props")
    assert "core_clk" in ports
    assert "we" in ports and "rdata" in ports
    assert "rst_n" not in ports and "rst_pyc" not in ports
    check_leaf_ports(ports, module="ub_cmn_mem_1r1w_if_props")


def test_parse_module_ports_core_clk_no_reset():
    text = """
module ub_cmn_mem_1r1w_d5w8 (
  input core_clk,
  input we,
  input [2:0] waddr,
  input [7:0] wdata,
  input re,
  input [2:0] raddr,
  output [7:0] rdata
);
endmodule
"""
    ports = parse_module_ports(text, "ub_cmn_mem_1r1w_d5w8")
    assert ports == (
        "core_clk",
        "we",
        "waddr",
        "wdata",
        "re",
        "raddr",
        "rdata",
    )
    check_leaf_ports(ports, module="ub_cmn_mem_1r1w_d5w8")


def test_check_leaf_ports_rejects_legacy_clk():
    ports = ("clk", "we", "waddr", "wdata", "re", "raddr", "rdata")
    try:
        check_leaf_ports(ports, module="ub_cmn_mem_1r1w_d5w8")
    except LeafPortError as exc:
        msg = str(exc)
        assert CLK_MISMATCH_ZH in msg
        assert "clk" in msg
        assert "silently" in msg
    else:
        raise AssertionError("expected LeafPortError for legacy clk")


def test_check_leaf_ports_rejects_any_reset():
    ports = (
        "core_clk",
        "rst_pyc",
        "we",
        "waddr",
        "wdata",
        "re",
        "raddr",
        "rdata",
    )
    try:
        check_leaf_ports(ports, module="ub_cmn_mem_1r1w_d5w8")
    except LeafPortError as exc:
        assert RST_FORBIDDEN_ZH in str(exc)
        assert "rst_pyc" in str(exc)
    else:
        raise AssertionError("expected LeafPortError for unexpected reset port")


def test_current_product_clk_is_reported_not_remapped():
    """Design-B leaf still emits clk. TB must fail with the Xia clock name."""
    found = discover_by_netlist("product")
    for var in found:
        if "clk" in var.ports and CLK_PORT not in var.ports:
            try:
                require_variant_ports(var)
            except LeafPortError as exc:
                assert CLK_MISMATCH_ZH in str(exc)
            else:
                raise AssertionError(
                    f"{var.module} has clk but port check stayed silent"
                )


def test_repo_product_netlist_ports_are_parsed():
    """Live PRODUCT files: parse ports. Sim raises LeafPortError on mismatch."""
    found = discover_by_netlist("product")
    if not found:
        return
    for var in found:
        print(f"PRODUCT {var.module} ports={var.ports}", flush=True)
        assert var.ports, f"{var.module} ANSI port list was empty"
        try:
            require_variant_ports(var)
            print(
                f"  port check OK ({CLK_PORT}, no reset, "
                f"WMASK_W={var.wmask_w} NSEG={var.nseg})",
                flush=True,
            )
        except LeafPortError as exc:
            print(f"  port check FAIL (sim will error, no silent remap): {exc}", flush=True)


def _write_xia_leaf(
    path: Path,
    module: str,
    aw: int,
    width: int,
    *,
    wmask_n: int | None = None,
) -> Path:
    wmask_decl = f"  input [{wmask_n}-1:0] wmask,\n" if wmask_n else ""
    path.write_text(
        f"""
module {module} (
  input core_clk,
  input we,
  input [{aw}-1:0] waddr,
  input [{width}-1:0] wdata,
{wmask_decl}  input re,
  input [{aw}-1:0] raddr,
  output [{width}-1:0] rdata
);
endmodule
""",
        encoding="utf-8",
    )
    return path


def test_parse_d64w64m16_tag(tmp_path: Path):
    path = _write_xia_leaf(
        tmp_path / f"{LEAF}_d64w64m16.v", f"{LEAF}_d64w64m16", 6, 64, wmask_n=4
    )
    var = parse_variant_file(path, netlist="product")
    assert var is not None
    assert (var.depth, var.width, var.wmask_w, var.nseg) == (64, 64, 16, 4)
    assert var.tag == "d64w64m16"
    assert "wmask" in var.ports
    assert var.extras.get("wmask_width") == 4
    require_variant_ports(var)


def test_parse_d512w512m64_tag(tmp_path: Path):
    path = _write_xia_leaf(
        tmp_path / f"{LEAF}_d512w512m64.v", f"{LEAF}_d512w512m64", 9, 512, wmask_n=8
    )
    var = parse_variant_file(path, netlist="product")
    assert var is not None
    assert (var.depth, var.width, var.wmask_w, var.nseg) == (512, 512, 64, 8)
    require_variant_ports(var)


def test_nseg_gt1_missing_wmask_errors(tmp_path: Path):
    path = _write_xia_leaf(
        tmp_path / f"{LEAF}_d64w64m16.v", f"{LEAF}_d64w64m16", 6, 64
    )
    var = parse_variant_file(path, netlist="product")
    assert var is not None and var.nseg == 4
    try:
        require_variant_ports(var)
    except LeafPortError as exc:
        assert WMASK_MISSING_ZH in str(exc)
    else:
        raise AssertionError("expected LeafPortError for missing wmask")


def test_nseg_gt1_wrong_wmask_width_errors(tmp_path: Path):
    path = _write_xia_leaf(
        tmp_path / f"{LEAF}_d64w64m16.v", f"{LEAF}_d64w64m16", 6, 64, wmask_n=8
    )
    var = parse_variant_file(path, netlist="product")
    assert var is not None
    try:
        require_variant_ports(var)
    except LeafPortError as exc:
        assert WMASK_WIDTH_ZH in str(exc)
        assert "8" in str(exc) and "4" in str(exc)
    else:
        raise AssertionError("expected LeafPortError for wrong wmask width")


def test_nseg1_extra_wmask_errors(tmp_path: Path):
    path = _write_xia_leaf(
        tmp_path / f"{LEAF}_d5w8.v", f"{LEAF}_d5w8", 3, 8, wmask_n=1
    )
    var = parse_variant_file(path, netlist="product")
    assert var is not None and var.nseg == 1
    try:
        require_variant_ports(var)
    except LeafPortError as exc:
        assert WMASK_FORBIDDEN_ZH in str(exc)
    else:
        raise AssertionError("expected LeafPortError for extra wmask on NSEG=1")


def test_check_wmask_port_direct():
    ok = ("core_clk", "we", "waddr", "wdata", "re", "raddr", "rdata")
    check_wmask_port(ok, nseg=1, module="n1")
    check_wmask_port(ok + ("wmask",), nseg=4, wmask_width=4, module="n4")
    try:
        check_wmask_port(ok, nseg=4, module="n4")
    except LeafPortError as exc:
        assert WMASK_MISSING_ZH in str(exc)
    else:
        raise AssertionError("expected missing-wmask error")


def test_emit_wrapper_wmask_when_nseg_gt1(tmp_path: Path):
    dest = tmp_path / "wrap_m16.sv"
    emit_wrapper(
        dest,
        dut_module=f"{LEAF}_d64w64m16",
        depth=64,
        width=64,
        wmask_w=16,
        assert_no_uninit_read=True,
        tb_check=True,
    )
    text = dest.read_text(encoding="utf-8")
    assert "input  wire [4-1:0] wmask" in text
    assert ".wmask (wmask)" in text
    assert ".wmask    (wmask)" in text
    assert ".WMASK_W(WMASK_W)" in text
    assert "localparam integer WMASK_W = 16" in text
    assert f"{LEAF}_d64w64m16 #(" not in text
    assert "rst_n" not in text
    assert "rst_pyc" not in text
