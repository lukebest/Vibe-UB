// Standalone stub: 2-flop async-assert / sync-deassert (SPEC §4.2).
// Not product RTL. Exists so reset.sby can pass without the real cell.

module ub_rst_sync_stub (
  input  wire core_clk,
  input  wire rst_n,
  output wire rst_n_sync
);
  reg r1;
  reg r2;

  always @(posedge core_clk or negedge rst_n) begin
    if (!rst_n) begin
      r1 <= 1'b0;
      r2 <= 1'b0;
    end else begin
      r1 <= 1'b1;
      r2 <= r1;
    end
  end

  assign rst_n_sync = r2;
endmodule

module ub_rst_harness (
  input wire core_clk,
  input wire rst_n
);
  initial assume (rst_n == 1'b0);
  wire rst_n_sync;

  ub_rst_sync_stub u_dut (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .rst_n_sync(rst_n_sync)
  );

  ub_rst_if_props u_props (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .rst_n_sync(rst_n_sync)
  );
endmodule
