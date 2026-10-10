"""Emit a per-variant TB wrapper. Constants are baked in — no Verilator ``-G``.

The product leaf is instantiated with no parameter overrides (SPEC §2.2).
``ub_cmn_mem_1r1w_if_props`` is connected the same way as ``formal/cmn``
(``core_clk`` / ``rst_n`` / we / waddr / wdata / re / raddr / rdata;
f_addr / f_written open). ASSERT_NO_UNINIT_READ lives on that bind, not
on the leaf. Array and rdata are not reset.
"""

from __future__ import annotations

from pathlib import Path

from model.ub_cmn_mem_1r1w import clog2
from tb.cmn.ports import CLK_PORT, RST_PORT

TOPLEVEL = "ub_cmn_mem_1r1w_tb"


def emit_wrapper(
    dest: Path,
    *,
    dut_module: str,
    depth: int,
    width: int,
    assert_no_uninit_read: bool,
    tb_check: bool,
) -> Path:
    aw = max(1, clog2(int(depth)))
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = (
        f"""// Generated TB wrapper. Not product RTL. Do not hand-edit.
// SPEC §2.2: leaf `{dut_module}` is a fixed netlist (no Verilog parameter).
// Clock/reset: {CLK_PORT} / {RST_PORT} (Xia; existing rtl/ leaves use rst_n).
// formal/cmn bind: ub_cmn_mem_1r1w_if_props (ASSERT_NO_UNINIT_READ on the bind).
`timescale 1ns / 1ps

module {TOPLEVEL} (
  input  wire             {CLK_PORT},
  input  wire             {RST_PORT},
  input  wire             we,
  input  wire [{aw}-1:0]  waddr,
  input  wire [{int(width)}-1:0] wdata,
  input  wire             re,
  input  wire [{aw}-1:0]  raddr,
  output wire [{int(width)}-1:0] rdata
);
  localparam integer DEPTH = {int(depth)};
  localparam integer WIDTH = {int(width)};
  localparam integer AW    = {aw};
  localparam integer ASSERT_NO_UNINIT_READ = {int(bool(assert_no_uninit_read))};
  localparam bit     TB_CHECK = 1'b{int(bool(tb_check))};

  {dut_module} u_dut (
    .{CLK_PORT} ({CLK_PORT}),
    .{RST_PORT}    ({RST_PORT}),
    .we    (we),
    .waddr (waddr),
    .wdata (wdata),
    .re    (re),
    .raddr (raddr),
    .rdata (rdata)
  );

  generate
    if (TB_CHECK) begin : g_formal_bind
      // Same port list as formal/cmn (Xia: core_clk + rst_n).
      wire [AW-1:0] f_addr;
      wire          f_written;
      ub_cmn_mem_1r1w_if_props #(
        .DEPTH(DEPTH),
        .WIDTH(WIDTH),
        .AW(AW),
        .ASSERT_NO_UNINIT_READ(ASSERT_NO_UNINIT_READ)
      ) u_props (
        .{CLK_PORT} ({CLK_PORT}),
        .{RST_PORT}    ({RST_PORT}),
        .we       (we),
        .waddr    (waddr),
        .wdata    (wdata),
        .re       (re),
        .raddr    (raddr),
        .rdata    (rdata),
        .f_addr   (f_addr),
        .f_written(f_written)
      );
    end
  endgenerate
endmodule
"""
    )
    if not dest.exists() or dest.read_text(encoding="utf-8") != text:
        dest.write_text(text, encoding="utf-8")
    return dest
