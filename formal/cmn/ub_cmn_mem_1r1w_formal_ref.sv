// FORMAL-ONLY synthesizable behavioral reference. NOT product RTL.
// Product leaf: pycc from pycircuit/cmn/ → rtl/cmn/ (design-B).
// Do not copy this array into a product path. No written-bit vector here
// (that lives in ub_cmn_mem_1r1w_if_props). Addresses are not truncated;
// out-of-range is an assertion, not a wrap. Clock is core_clk; no rst_pyc.

module ub_cmn_mem_1r1w_formal_ref #(
  parameter DEPTH = 5,
  parameter WIDTH = 8,
  parameter AW    = 3
) (
  input  wire             core_clk,
  input  wire             we,
  input  wire [AW-1:0]    waddr,
  input  wire [WIDTH-1:0] wdata,
  input  wire             re,
  input  wire [AW-1:0]    raddr,
  output reg  [WIDTH-1:0] rdata
);
  reg [WIDTH-1:0] mem [0:DEPTH-1];

  always @(posedge core_clk) begin
    if (re && (raddr < DEPTH))
      rdata <= mem[raddr];
    if (we && (waddr < DEPTH))
      mem[waddr] <= wdata;
  end
endmodule
