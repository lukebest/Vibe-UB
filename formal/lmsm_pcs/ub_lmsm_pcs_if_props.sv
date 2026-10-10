// ub_lmsm_pcs_if_props — property-only LMSM→PCS control (SPEC §3.3.4).
// Bind on LMSM outputs + the PCS latched copies. No RTL logic.
//
// lmb_start is the PCS "LMB about to start" strobe (not a SPEC top-level pin;
// design and TB bind it to the insertion-boundary pulse).

module ub_lmsm_pcs_if_props (
  input wire       core_clk,
  input wire       rst_n,
  input wire       lmb_start,
  input wire [1:0] lmsm2pcs_pattern,
  input wire [1:0] lmsm2pcs_lane_id_mode,
  input wire       lmsm2pcs_ltb_valid,
  input wire [7:0] lmsm2pcs_ltb_type,
  input wire [1:0] latched_pattern,
  input wire [1:0] latched_lane_id_mode,
  input wire       latched_ltb_valid,
  input wire [7:0] latched_ltb_type
);

  // SPEC §3.3.4: lmsm2pcs_pattern[1:0] encodings 0..3 are all legal
  // (0 idle, 1 EEIB, 2 LTB, 3 DLL). A 2-bit net is always 0..3; covers hit each.
  always @(*) begin
    a_pattern_in_0_3: assert (lmsm2pcs_pattern <= 2'd3);
  end
  c_pattern_idle: cover property (@(posedge core_clk) rst_n && (lmsm2pcs_pattern == 2'd0));
  c_pattern_eeib: cover property (@(posedge core_clk) rst_n && (lmsm2pcs_pattern == 2'd1));
  c_pattern_ltb:  cover property (@(posedge core_clk) rst_n && (lmsm2pcs_pattern == 2'd2));
  c_pattern_dll:  cover property (@(posedge core_clk) rst_n && (lmsm2pcs_pattern == 2'd3));

  // SPEC §3.3.4: lane_id_mode 0=PHYS, 1=ASCEND, 2=NULL; 3=RESERVED.
  // LMSM never drives 3 (TB assert). PCS treats 3 as NULL if a leaf TB forces it.
  a_lane_id_mode_ne3: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    lmsm2pcs_lane_id_mode != 2'd3
  );
  c_mode_phys:   cover property (@(posedge core_clk) rst_n && (lmsm2pcs_lane_id_mode == 2'd0));
  c_mode_ascend: cover property (@(posedge core_clk) rst_n && (lmsm2pcs_lane_id_mode == 2'd1));
  c_mode_null:   cover property (@(posedge core_clk) rst_n && (lmsm2pcs_lane_id_mode == 2'd2));

  // SPEC §3.3.4 / §5: all lmsm2pcs_* fields + pattern + lane_id_* latch at
  // the LMB start boundary. Mid-frame changes take effect at the next LMB.
  // lmsm2pcs_ltb_valid has no multi-cycle hold requirement (cover a pulse).
  a_latch_pattern: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    lmb_start |=> (latched_pattern == $past(lmsm2pcs_pattern))
  );
  a_latch_mode: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    lmb_start |=> (latched_lane_id_mode == $past(lmsm2pcs_lane_id_mode))
  );
  a_latch_ltb_valid: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    lmb_start |=> (latched_ltb_valid == $past(lmsm2pcs_ltb_valid))
  );
  a_latch_ltb_type: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    lmb_start |=> (latched_ltb_type == $past(lmsm2pcs_ltb_type))
  );

  a_hold_pattern: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    !lmb_start |=> $stable(latched_pattern)
  );
  a_hold_mode: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    !lmb_start |=> $stable(latched_lane_id_mode)
  );

  c_lmb_start: cover property (@(posedge core_clk) rst_n && lmb_start);
  c_ltb_valid_pulse: cover property (
    @(posedge core_clk) rst_n && lmsm2pcs_ltb_valid && !$past(lmsm2pcs_ltb_valid)
  );
  c_change_before_lmb: cover property (
    @(posedge core_clk) rst_n && !lmb_start && !$stable(lmsm2pcs_pattern)
  );

endmodule
