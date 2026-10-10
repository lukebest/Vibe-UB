// FORMAL-ONLY synthesizable behavioral reference. NOT product RTL.
// Product leaf: pycc from pycircuit/cmn/ → rtl/cmn/ (design-B).
// Do not copy this array into a product path. No written-bit vector here
// (that lives in ub_cmn_mem_1r1w_if_props). Addresses are not truncated;
// out-of-range is an assertion, not a wrap. Clock is core_clk; no rst_pyc.
//
// WMASK_W default WIDTH. NSEG>1: wmask[i] writes segment i; others hold.
// ABSTRACT=1 keeps a single watched word (f_focus) so large DEPTH
// (d64w64m16) converges; the anyconst in the property module still
// quantifies over every legal address.

module ub_cmn_mem_1r1w_formal_ref #(
  parameter DEPTH   = 5,
  parameter WIDTH   = 8,
  parameter AW      = 3,
  parameter WMASK_W = WIDTH,
  parameter ABSTRACT = 0
) (
  input  wire             core_clk,
  input  wire             we,
  input  wire [AW-1:0]    waddr,
  input  wire [WIDTH-1:0] wdata,
  input  wire [WIDTH/WMASK_W-1:0] wmask,
  input  wire             re,
  input  wire [AW-1:0]    raddr,
  input  wire [AW-1:0]    f_focus,
  output reg  [WIDTH-1:0] rdata
);
  localparam NSEG = WIDTH / WMASK_W;

  wire [NSEG-1:0] wmask_eff = (NSEG == 1) ? {NSEG{1'b1}} : wmask;

  integer si;

  generate
    if (ABSTRACT != 0) begin : g_abs
      reg [WIDTH-1:0] cell;
      always @(posedge core_clk) begin
        if (re && (raddr == f_focus) && (raddr < DEPTH))
          rdata <= cell;
        if (we && (waddr == f_focus) && (waddr < DEPTH)) begin
          for (si = 0; si < NSEG; si = si + 1) begin
            if (wmask_eff[si])
              cell[si*WMASK_W +: WMASK_W] <= wdata[si*WMASK_W +: WMASK_W];
          end
        end
      end
    end else begin : g_full
      reg [WIDTH-1:0] mem [0:DEPTH-1];
      always @(posedge core_clk) begin
        if (re && (raddr < DEPTH))
          rdata <= mem[raddr];
        if (we && (waddr < DEPTH)) begin
          for (si = 0; si < NSEG; si = si + 1) begin
            if (wmask_eff[si])
              mem[waddr][si*WMASK_W +: WMASK_W] <= wdata[si*WMASK_W +: WMASK_W];
          end
        end
      end
    end
  endgenerate
endmodule
