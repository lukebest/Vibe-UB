// PLACEHOLDER — local lint / directed smoke only.
// Not a product netlist. Do not commit a fake primitive into rtl/.
//
// Port list and timing match design-B PR #21 / CODING_STYLE §10:
//   1R1W, registered read (1 cycle), same-address read-old, no reset.
// Replace with PR #21 `ub_cmn_mem_1r1w_d64w109` when that leaf is on main.

`ifndef UB_CMN_MEM_1R1W_D64W109_PLACEHOLDER
`define UB_CMN_MEM_1R1W_D64W109_PLACEHOLDER

module ub_cmn_mem_1r1w_d64w109 (
  input              core_clk,
  input              we,
  input        [5:0] waddr,
  input      [108:0] wdata,
  input              re,
  input        [5:0] raddr,
  output     [108:0] rdata
);
  reg [108:0] mem [0:63];
  reg [108:0] rdata_q;

  always @(posedge core_clk) begin
    if (we)
      mem[waddr] <= wdata;
    if (re)
      rdata_q <= mem[raddr];
  end

  assign rdata = rdata_q;
endmodule

`endif
