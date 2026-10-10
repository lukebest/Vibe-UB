// Legal irq stub: reset-masked, active-high OR of unmasked sources.
// Not product RTL.

module ub_irq_stub (
  input  wire       core_clk,
  input  wire       rst_n,
  input  wire       wr_en,
  input  wire       wr_mask,
  input  wire       wr_status,
  input  wire       en_nxt,
  input  wire [6:0] mask_nxt,
  input  wire [6:0] status_nxt,
  output reg        irq_en,
  output reg  [6:0] irq_mask,
  output reg  [6:0] irq_status,
  output wire       irq
);
  assign irq = irq_en && |(irq_status & ~irq_mask);

  always @(posedge core_clk) begin
    if (!rst_n) begin
      irq_en     <= 1'b0;
      irq_mask   <= 7'h7F;
      irq_status <= 7'h00;
    end else begin
      if (wr_en)
        irq_en <= en_nxt;
      if (wr_mask)
        irq_mask <= mask_nxt;
      if (wr_status)
        irq_status <= status_nxt;
    end
  end
endmodule

module ub_irq_harness (
  input wire       core_clk,
  input wire       rst_n,
  input wire       wr_en,
  input wire       wr_mask,
  input wire       wr_status,
  input wire       en_nxt,
  input wire [6:0] mask_nxt,
  input wire [6:0] status_nxt
);
  initial assume (rst_n == 1'b0);
  wire       irq_en;
  wire [6:0] irq_mask;
  wire [6:0] irq_status;
  wire       irq;

  ub_irq_stub u_dut (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .wr_en(wr_en),
    .wr_mask(wr_mask),
    .wr_status(wr_status),
    .en_nxt(en_nxt),
    .mask_nxt(mask_nxt),
    .status_nxt(status_nxt),
    .irq_en(irq_en),
    .irq_mask(irq_mask),
    .irq_status(irq_status),
    .irq(irq)
  );

  ub_irq_if_props u_props (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .irq(irq),
    .irq_en(irq_en),
    .irq_status(irq_status),
    .irq_mask(irq_mask)
  );
endmodule
