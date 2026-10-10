// ub_irq_if_props — property-only top-level irq (SPEC §3.2.6, REGMAP §2.1).
// Bind on ub_controller irq / IRQ_EN / IRQ_STATUS / IRQ_MASK. No RTL logic.

module ub_irq_if_props (
  input wire       core_clk,
  input wire       rst_n,
  input wire       irq,
  input wire       irq_en,
  input wire [6:0] irq_status,
  input wire [6:0] irq_mask
);

  // SPEC §3.2.6 / REGMAP §2.1: irq is active-high.
  // irq = IRQ_EN & |(IRQ_STATUS & ~IRQ_MASK).
  a_irq_formula: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    irq == (irq_en && |(irq_status & ~irq_mask))
  );

  // SPEC §3.2.6 / REGMAP §2.1: reset masks every source
  // (IRQ_MASK=0x7F, IRQ_EN=0) so irq is 0.
  a_irq_reset_mask: assert property (
    @(posedge core_clk)
    !rst_n |-> (!irq_en && (irq_mask == 7'h7F) && !irq)
  );

  // First cycle after sync release still shows the reset mask (sampled).
  a_irq_release_masked: assert property (
    @(posedge core_clk)
    rst_n && !$past(rst_n) |-> (!irq_en && (irq_mask == 7'h7F) && !irq)
  );

  c_irq_masked_zero: cover property (
    @(posedge core_clk) rst_n && (irq_mask == 7'h7F) && !irq
  );
  c_irq_unmasked_fire: cover property (
    @(posedge core_clk) rst_n && irq_en && irq
  );
  c_irq_en0_quiet: cover property (
    @(posedge core_clk) rst_n && !irq_en && |irq_status && !irq
  );

endmodule
