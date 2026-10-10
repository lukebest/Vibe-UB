// ub_rst_if_props — property-only. Bind or instantiate; no RTL logic.
// Design:  bind ub_rst_sync ub_rst_if_props u_if (.*);
// Verification: instantiate beside the whitelist cell / TB wrapper.
//
// Ports match the whitelist cell (CODING_STYLE §3): core_clk, rst_n, rst_n_sync.

module ub_rst_if_props (
  input wire core_clk,
  input wire rst_n,
  input wire rst_n_sync
);

  // SPEC §4.2 / CODING_STYLE §2: rst_n is active-low; async assert.
  // While the pin is 0, the synchronizer output must already be 0
  // (does not wait for core_clk).
  always @(*) begin
    if (rst_n == 1'b0)
      a_rst_async_assert: assert (rst_n_sync == 1'b0);
  end

  // SPEC §4.2: sync deassert through a 2-flop ub_rst_sync.
  // Two consecutive sampled rst_n==1 imply rst_n_sync==1 on the next edge
  // (second flop has then absorbed the first).
  a_rst_sync_deassert_2flop: assert property (
    @(posedge core_clk)
    rst_n && $past(rst_n) |=> rst_n_sync
  );

  // SPEC §4.2: a sampled assert forces the next-cycle output to stay 0
  // (flop chain cleared). Combined with the combo assert above.
  a_rst_held_after_assert: assert property (
    @(posedge core_clk)
    !rst_n |=> !rst_n_sync
  );

  // Covers: release (output rises) and re-assert (output falls).
  c_rst_n_sync_rise: cover property (@(posedge core_clk) rst_n_sync && !$past(rst_n_sync));
  c_rst_n_sync_fall: cover property (@(posedge core_clk) !rst_n_sync && $past(rst_n_sync));
  c_rst_n_asserted:  cover property (@(posedge core_clk) !rst_n);
  c_rst_n_released:  cover property (@(posedge core_clk) rst_n && rst_n_sync);

endmodule
