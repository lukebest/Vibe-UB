// ub_rst_if_props — property-only. Bind or instantiate; no RTL datapath.
// Design:  bind ub_rst_sync ub_rst_if_props u_if (.*);
// Verification: instantiate beside the whitelist cell / TB wrapper.
// Yosys-compatible subset: clocked assert/cover (no Verific concurrent SVA).
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

  // Formal window only — not DUT logic. $past is free before enough clocks.
  reg [1:0] f_age;
  initial f_age = 2'b00;
  always @(posedge core_clk)
    f_age <= {f_age[0], 1'b1};

  always @(posedge core_clk) begin
    // SPEC §4.2: sync deassert through a 2-flop ub_rst_sync.
    // Two consecutive sampled rst_n==1 imply rst_n_sync==1 on the next edge.
    // Current rst_n must still be 1: an async assert this cycle clears both flops.
    if (f_age[1] && rst_n && $past(rst_n) && $past(rst_n, 2))
      a_rst_sync_deassert_2flop: assert (rst_n_sync);

    // SPEC §4.2: a sampled assert forces the next-cycle output to stay 0.
    if (f_age[0] && $past(!rst_n))
      a_rst_held_after_assert: assert (!rst_n_sync);

    c_rst_n_sync_rise: cover (rst_n_sync && !$past(rst_n_sync));
    c_rst_n_sync_fall: cover (!rst_n_sync && $past(rst_n_sync));
    c_rst_n_asserted:  cover (!rst_n);
    c_rst_n_released:  cover (rst_n && rst_n_sync);
  end

endmodule
