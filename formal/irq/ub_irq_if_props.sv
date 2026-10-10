// ub_irq_if_props — property-only top-level irq (SPEC §3.2.6, REGMAP §2.1).
// Bind on ub_controller irq / IRQ_EN / IRQ_STATUS / IRQ_MASK. No RTL datapath.
// CSR side is synchronously reset (rst_n here is rst_n_sync / rst_pyc).

module ub_irq_if_props (
  input wire       core_clk,
  input wire       rst_n,
  input wire       irq,
  input wire       irq_en,
  input wire [6:0] irq_status,
  input wire [6:0] irq_mask
);

  reg f_past_ok;
  initial f_past_ok = 1'b0;
  always @(posedge core_clk)
    f_past_ok <= 1'b1;

  always @(posedge core_clk) begin
    // SPEC §3.2.6 / REGMAP §2.1: after a cycle of reset, every source is
    // masked (IRQ_MASK=0x7F, IRQ_EN=0) so irq is 0.
    if (f_past_ok && $past(!rst_n))
      a_irq_reset_mask: assert (!irq_en && (irq_mask == 7'h7F) && !irq);

    if (rst_n) begin
      // SPEC §3.2.6 / REGMAP §2.1: irq is active-high.
      // irq = IRQ_EN & |(IRQ_STATUS & ~IRQ_MASK).
      a_irq_formula: assert (irq == (irq_en && |(irq_status & ~irq_mask)));

      // First cycle after sync release still shows the reset mask (sampled).
      if (f_past_ok && !$past(rst_n))
        a_irq_release_masked: assert (!irq_en && (irq_mask == 7'h7F) && !irq);

      c_irq_masked_zero:   cover ((irq_mask == 7'h7F) && !irq);
      c_irq_unmasked_fire: cover (irq_en && irq);
      c_irq_en0_quiet:     cover (!irq_en && |irq_status && !irq);
    end
  end

endmodule
