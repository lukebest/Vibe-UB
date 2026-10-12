// Standalone harness: formal-only ref + props. Not product RTL.
// Environment assumes keep BMC from driving OOR / uninit reads so the
// DUT data properties are provable. Bind-time TB may omit these assumes.
//
// Default elaboration is the existing whole-word small config (d5w8).
// ub_cmn_mem_1r1w_harness_m16 is d64w64m16 (NSEG=4) with one-address
// abstraction so the large array still converges.

module ub_cmn_mem_1r1w_harness #(
  parameter DEPTH   = 5,
  parameter WIDTH   = 8,
  parameter AW      = 3,
  parameter WMASK_W = WIDTH,
  parameter ASSERT_NO_UNINIT_READ = 1,
  parameter ABSTRACT = 0
) (
  input wire             core_clk,
  input wire             we,
  input wire [AW-1:0]    waddr,
  input wire [WIDTH-1:0] wdata,
  input wire [WIDTH/WMASK_W-1:0] wmask,
  input wire             re,
  input wire [AW-1:0]    raddr
);
  localparam NSEG = WIDTH / WMASK_W;

  wire [WIDTH-1:0] rdata;
  wire [AW-1:0]    f_addr;
  wire [NSEG-1:0]  f_written;
  wire [NSEG-1:0]  wmask_eff = (NSEG == 1) ? {NSEG{1'b1}} : wmask;

  always @(*) begin
    if (we)
      assume (waddr < DEPTH);
    if (re)
      assume (raddr < DEPTH);
    if (NSEG == 1)
      assume (wmask == {NSEG{1'b1}});
  end

  always @(posedge core_clk) begin
    if (ASSERT_NO_UNINIT_READ && re && (raddr == f_addr) && (raddr < DEPTH))
      assume (f_written == {NSEG{1'b1}});
  end

  ub_cmn_mem_1r1w_formal_ref #(
    .DEPTH(DEPTH), .WIDTH(WIDTH), .AW(AW),
    .WMASK_W(WMASK_W), .ABSTRACT(ABSTRACT)
  ) u_dut (
    .core_clk(core_clk),
    .we(we),
    .waddr(waddr),
    .wdata(wdata),
    .wmask(wmask_eff),
    .re(re),
    .raddr(raddr),
    .f_focus(f_addr),
    .rdata(rdata)
  );

  ub_cmn_mem_1r1w_if_props #(
    .DEPTH(DEPTH), .WIDTH(WIDTH), .AW(AW),
    .WMASK_W(WMASK_W),
    .ASSERT_NO_UNINIT_READ(ASSERT_NO_UNINIT_READ)
  ) u_props (
    .core_clk(core_clk),
    .we(we),
    .waddr(waddr),
    .wdata(wdata),
    .wmask(wmask_eff),
    .re(re),
    .raddr(raddr),
    .rdata(rdata),
    .f_addr(f_addr),
    .f_written(f_written)
  );
endmodule

// Small masked formal/gate variant: DEPTH=64 WIDTH=64 WMASK_W=16 (NSEG=4).
module ub_cmn_mem_1r1w_harness_m16 (
  input wire        core_clk,
  input wire        we,
  input wire [5:0]  waddr,
  input wire [63:0] wdata,
  input wire [3:0]  wmask,
  input wire        re,
  input wire [5:0]  raddr
);
  ub_cmn_mem_1r1w_harness #(
    .DEPTH(64), .WIDTH(64), .AW(6), .WMASK_W(16),
    .ASSERT_NO_UNINIT_READ(1), .ABSTRACT(1)
  ) u (
    .core_clk(core_clk),
    .we(we),
    .waddr(waddr),
    .wdata(wdata),
    .wmask(wmask),
    .re(re),
    .raddr(raddr)
  );
endmodule
