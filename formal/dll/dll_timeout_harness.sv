// DLL / LMSM timeout harness. No product RTL. Combo-of-cyc.
// RETRY_WAIT_CYC is DLL (§4.7.3.3); PROBE_WAIT_CYC is LMSM (§3.4.3.2).
`default_nettype none

module dll_timeout_harness (
  input wire core_clk
);
  reg [3:0] cyc;
  initial cyc = 4'd0;
  always @(posedge core_clk) begin
    if (cyc != 4'd15)
      cyc <= cyc + 4'd1;
  end

  wire rst_n = (cyc != 4'd0);
  wire [15:0] retry_elapsed   = (cyc == 4'd2) ? 16'd322 :
                                (cyc == 4'd3) ? 16'd323 : 16'd0;
  wire        retry_timed_out = (retry_elapsed >= 16'd323);
  wire [15:0] probe_elapsed   = (cyc == 4'd4) ? 16'd322 :
                                (cyc == 4'd5) ? 16'd323 : 16'd0;
  wire        probe_timed_out = (probe_elapsed >= 16'd323);

  dll_timeout_assert u_dll_timeout_assert (
    .core_clk        (core_clk),
    .rst_n           (rst_n),
    .retry_elapsed   (retry_elapsed),
    .retry_timed_out (retry_timed_out),
    .probe_elapsed   (probe_elapsed),
    .probe_timed_out (probe_timed_out)
  );
endmodule

`default_nettype wire
