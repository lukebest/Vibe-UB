// ub_rst_sync — whitelist handwritten SystemVerilog (CODING_STYLE §3, SPEC §4.2 / §4.3).
// 2-stage async-assert / sync-deassert. Clocked by core_clk. Output rst_n_sync.
// Review record: Vibe-UB RTL batch-1 PR (stacked on docs-m1-architecture).
// Stages = 2 (CODING_STYLE §2 / SPEC §4.2; design-side readiness review).
// Business logic must NOT use this cell's async style; only the top-level rst_n path.
// core_clk must be running for sync release to propagate (sync deassert).

module ub_rst_sync (
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
