// Standalone harness: formal-only ref + props. Not product RTL.
// Environment assumes keep BMC from driving OOR / uninit reads so the
// DUT data properties are provable. Bind-time TB may omit these assumes.

module ub_cmn_mem_1r1w_harness #(
  parameter DEPTH = 5,
  parameter WIDTH = 8,
  parameter AW    = 3,
  parameter ASSERT_NO_UNINIT_READ = 1
) (
  input wire             clk,
  input wire             we,
  input wire [AW-1:0]    waddr,
  input wire [WIDTH-1:0] wdata,
  input wire             re,
  input wire [AW-1:0]    raddr
);
  wire [WIDTH-1:0] rdata;
  wire [AW-1:0]    f_addr;
  wire             f_written;

  always @(*) begin
    if (we)
      assume (waddr < DEPTH);
    if (re)
      assume (raddr < DEPTH);
  end

  always @(posedge clk) begin
    if (ASSERT_NO_UNINIT_READ && re && (raddr == f_addr) && (raddr < DEPTH))
      assume (f_written);
  end

  ub_cmn_mem_1r1w_formal_ref #(
    .DEPTH(DEPTH), .WIDTH(WIDTH), .AW(AW)
  ) u_dut (
    .clk(clk),
    .we(we),
    .waddr(waddr),
    .wdata(wdata),
    .re(re),
    .raddr(raddr),
    .rdata(rdata)
  );

  ub_cmn_mem_1r1w_if_props #(
    .DEPTH(DEPTH), .WIDTH(WIDTH), .AW(AW),
    .ASSERT_NO_UNINIT_READ(ASSERT_NO_UNINIT_READ)
  ) u_props (
    .clk(clk),
    .we(we),
    .waddr(waddr),
    .wdata(wdata),
    .re(re),
    .raddr(raddr),
    .rdata(rdata),
    .f_addr(f_addr),
    .f_written(f_written)
  );
endmodule
