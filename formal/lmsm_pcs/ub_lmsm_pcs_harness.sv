// Legal LMSM→PCS stub: never drives lane_id_mode=3; latches at lmb_start.
// Not product RTL.

module ub_lmsm_pcs_stub (
  input  wire       core_clk,
  input  wire       rst_n,
  input  wire       lmb_start,
  input  wire [1:0] pattern_in,
  input  wire [1:0] mode_in,
  input  wire       ltb_valid_in,
  input  wire [7:0] ltb_type_in,
  output wire [1:0] lmsm2pcs_pattern,
  output wire [1:0] lmsm2pcs_lane_id_mode,
  output wire       lmsm2pcs_ltb_valid,
  output wire [7:0] lmsm2pcs_ltb_type,
  output reg  [1:0] latched_pattern,
  output reg  [1:0] latched_lane_id_mode,
  output reg        latched_ltb_valid,
  output reg  [7:0] latched_ltb_type
);
  // SPEC §3.3.4: LMSM never drives RESERVED (3). Stub folds 3 → NULL (2).
  assign lmsm2pcs_pattern       = pattern_in;
  assign lmsm2pcs_lane_id_mode  = (mode_in == 2'd3) ? 2'd2 : mode_in;
  assign lmsm2pcs_ltb_valid     = ltb_valid_in;
  assign lmsm2pcs_ltb_type      = ltb_type_in;

  always @(posedge core_clk) begin
    if (!rst_n) begin
      latched_pattern       <= 2'd0;
      latched_lane_id_mode  <= 2'd0;
      latched_ltb_valid     <= 1'b0;
      latched_ltb_type      <= 8'd0;
    end else if (lmb_start) begin
      latched_pattern       <= lmsm2pcs_pattern;
      latched_lane_id_mode  <= lmsm2pcs_lane_id_mode;
      latched_ltb_valid     <= lmsm2pcs_ltb_valid;
      latched_ltb_type      <= lmsm2pcs_ltb_type;
    end
  end
endmodule

module ub_lmsm_pcs_harness (
  input wire       core_clk,
  input wire       rst_n,
  input wire       lmb_start,
  input wire [1:0] pattern_in,
  input wire [1:0] mode_in,
  input wire       ltb_valid_in,
  input wire [7:0] ltb_type_in
);
  wire [1:0] lmsm2pcs_pattern;
  wire [1:0] lmsm2pcs_lane_id_mode;
  wire       lmsm2pcs_ltb_valid;
  wire [7:0] lmsm2pcs_ltb_type;
  wire [1:0] latched_pattern;
  wire [1:0] latched_lane_id_mode;
  wire       latched_ltb_valid;
  wire [7:0] latched_ltb_type;

  ub_lmsm_pcs_stub u_dut (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .lmb_start(lmb_start),
    .pattern_in(pattern_in),
    .mode_in(mode_in),
    .ltb_valid_in(ltb_valid_in),
    .ltb_type_in(ltb_type_in),
    .lmsm2pcs_pattern(lmsm2pcs_pattern),
    .lmsm2pcs_lane_id_mode(lmsm2pcs_lane_id_mode),
    .lmsm2pcs_ltb_valid(lmsm2pcs_ltb_valid),
    .lmsm2pcs_ltb_type(lmsm2pcs_ltb_type),
    .latched_pattern(latched_pattern),
    .latched_lane_id_mode(latched_lane_id_mode),
    .latched_ltb_valid(latched_ltb_valid),
    .latched_ltb_type(latched_ltb_type)
  );

  ub_lmsm_pcs_if_props u_props (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .lmb_start(lmb_start),
    .lmsm2pcs_pattern(lmsm2pcs_pattern),
    .lmsm2pcs_lane_id_mode(lmsm2pcs_lane_id_mode),
    .lmsm2pcs_ltb_valid(lmsm2pcs_ltb_valid),
    .lmsm2pcs_ltb_type(lmsm2pcs_ltb_type),
    .latched_pattern(latched_pattern),
    .latched_lane_id_mode(latched_lane_id_mode),
    .latched_ltb_valid(latched_ltb_valid),
    .latched_ltb_type(latched_ltb_type)
  );
endmodule
