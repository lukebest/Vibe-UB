"""Emit a per-variant TB wrapper. Constants are baked in — no Verilator ``-G``.

The product leaf is instantiated with no parameter overrides (SPEC §2.2).
``ub_cmn_mem_1r1w_if_props`` is connected the same way as ``formal/cmn``
(``core_clk`` / we / waddr / wdata / [wmask] / re / raddr / rdata; no reset;
f_addr / f_written open). ASSERT_NO_UNINIT_READ lives on that bind, not
on the leaf. Array and rdata are not reset.

``wmask`` is a wrapper port only when ``NSEG>1``. The bind pin is always
present: tied ``1'b1`` when ``NSEG=1``, connected to the DUT when ``NSEG>1``.
"""

from __future__ import annotations

from pathlib import Path

from model.ub_cmn_mem_1r1w import clog2
from tb.cmn.ports import CLK_PORT

TOPLEVEL = "ub_cmn_mem_1r1w_tb"


def emit_wrapper(
    dest: Path,
    *,
    dut_module: str,
    depth: int,
    width: int,
    assert_no_uninit_read: bool,
    tb_check: bool,
    wmask_w: int | None = None,
) -> Path:
    aw = max(1, clog2(int(depth)))
    wmask_w = int(width if wmask_w is None else wmask_w)
    nseg = int(width) // wmask_w
    dest.parent.mkdir(parents=True, exist_ok=True)
    if nseg > 1:
        wmask_top = f"  input  wire [{nseg}-1:0] wmask,\n"
        wmask_dut = "    .wmask (wmask),\n"
        wmask_bind = "        .wmask    (wmask),\n"
    else:
        wmask_top = ""
        wmask_dut = ""
        wmask_bind = "        .wmask    (1'b1),\n"
    text = (
        f"""// Generated TB wrapper. Not product RTL. Do not hand-edit.
// SPEC §2.2: leaf `{dut_module}` is a fixed netlist (no Verilog parameter).
// Clock: {CLK_PORT}. No reset port (Xia / CODING_STYLE §10).
// formal/cmn bind: ub_cmn_mem_1r1w_if_props (ASSERT_NO_UNINIT_READ on the bind).
// NSEG={nseg}: wmask is a leaf port only when NSEG>1; bind pin always present.
`timescale 1ns / 1ps

module {TOPLEVEL} (
  input  wire             {CLK_PORT},
  input  wire             we,
  input  wire [{aw}-1:0]  waddr,
  input  wire [{int(width)}-1:0] wdata,
{wmask_top}  input  wire             re,
  input  wire [{aw}-1:0]  raddr,
  output wire [{int(width)}-1:0] rdata
);
  localparam integer DEPTH = {int(depth)};
  localparam integer WIDTH = {int(width)};
  localparam integer AW    = {aw};
  localparam integer WMASK_W = {wmask_w};
  localparam integer NSEG  = WIDTH / WMASK_W;
  localparam integer ASSERT_NO_UNINIT_READ = {int(bool(assert_no_uninit_read))};
  localparam bit     TB_CHECK = 1'b{int(bool(tb_check))};

  {dut_module} u_dut (
    .{CLK_PORT} ({CLK_PORT}),
    .we    (we),
    .waddr (waddr),
    .wdata (wdata),
{wmask_dut}    .re    (re),
    .raddr (raddr),
    .rdata (rdata)
  );

  generate
    if (TB_CHECK) begin : g_formal_bind
      // Same port list as formal/cmn (Xia: core_clk, no reset; wmask always on bind).
      wire [AW-1:0] f_addr;
      wire [NSEG-1:0] f_written;
      ub_cmn_mem_1r1w_if_props #(
        .DEPTH(DEPTH),
        .WIDTH(WIDTH),
        .AW(AW),
        .WMASK_W(WMASK_W),
        .ASSERT_NO_UNINIT_READ(ASSERT_NO_UNINIT_READ)
      ) u_props (
        .{CLK_PORT} ({CLK_PORT}),
        .we       (we),
        .waddr    (waddr),
        .wdata    (wdata),
{wmask_bind}        .re       (re),
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
