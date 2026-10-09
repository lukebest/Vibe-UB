// Vendored from lukebest/pyCircuit @ 43cc5918 runtime/verilog/pyc_reg.v (pyc4.0).
// Native polarity is synchronous active-high `rst` (SPEC §4.2 / CODING_STYLE §2).
// Business leaves use this polarity via rst_pyc from ub_pyc_rst_adapt.

module pyc_reg #(
  parameter WIDTH = 1
) (
  input              clk,
  input              rst,
  input              en,
  input  [WIDTH-1:0] d,
  input  [WIDTH-1:0] init,
  output reg [WIDTH-1:0] q
);
  always @(posedge clk) begin
    if (rst)
      q <= init;
    else if (en)
      q <= d;
  end
endmodule
