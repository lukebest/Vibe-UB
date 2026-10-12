// DLL RETRY_WAIT + LMSM PROBE_WAIT 322/323 covers (SPEC §4.1 / §6.1 / §6.3).
// Moved out of formal/contracts/nw_tp (LAYER_CONTRACTS §3: those timers
// are not TP). TP formal keeps only RTO / ACK-coalesce covers.
// Immediate asserts for Yosys 0.33. No assume.
`default_nettype none

module dll_timeout_assert (
  input wire        core_clk,
  input wire        rst_n,
  input wire [15:0] retry_elapsed,
  input wire        retry_timed_out,
  input wire [15:0] probe_elapsed,
  input wire        probe_timed_out
);
  localparam integer TIMEOUT_DEF = 323;

  always @* begin
    a_timeout_def: assert (TIMEOUT_DEF == 323);
    a_retry_rel: assert (retry_timed_out == (retry_elapsed >= TIMEOUT_DEF[15:0]));
    a_probe_rel: assert (probe_timed_out == (probe_elapsed >= TIMEOUT_DEF[15:0]));
  end

  always @(posedge core_clk) begin
    c_timeout_322: cover (rst_n && retry_elapsed == 16'd322 && !retry_timed_out);
    c_timeout_323: cover (rst_n && retry_elapsed == 16'd323 && retry_timed_out);
    c_probe_322: cover (rst_n && probe_elapsed == 16'd322 && !probe_timed_out);
    c_probe_323: cover (rst_n && probe_elapsed == 16'd323 && probe_timed_out);
  end
endmodule

bind dll_timeout_harness dll_timeout_assert u_dll_timeout_assert (
  .core_clk         (core_clk),
  .rst_n            (rst_n),
  .retry_elapsed    (retry_elapsed),
  .retry_timed_out  (retry_timed_out),
  .probe_elapsed    (probe_elapsed),
  .probe_timed_out  (probe_timed_out)
);

`default_nettype wire
